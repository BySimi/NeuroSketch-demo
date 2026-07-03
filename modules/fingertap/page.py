import os
import time
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from modules.fingertap.detector import FingerTapProcessor, generate_graph


def get_ice_servers():
    """
    Returns ICE server configuration safely for both Hugging Face and Streamlit Cloud.
    """
    account_sid = None
    auth_token = None

    # 1. Safely check OS environment (Hugging Face standard)
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

    # 2. Safely check Streamlit secrets (Streamlit Cloud standard)
    if not account_sid or not auth_token:
        try:
            # hasattr prevents FileNotFoundError if the .toml file is completely missing
            if hasattr(st, "secrets") and "TWILIO_ACCOUNT_SID" in st.secrets:
                account_sid = st.secrets["TWILIO_ACCOUNT_SID"]
                auth_token = st.secrets["TWILIO_AUTH_TOKEN"]
        except Exception:
            # Catch FileNotFoundError, KeyError, etc. gracefully
            pass

    # 3. If we found credentials, fetch Twilio ICE servers
    if account_sid and auth_token:
        try:
            from twilio.rest import Client

            client = Client(account_sid, auth_token)
            token = client.tokens.create()
            return token.ice_servers
        except Exception as e:
            print(f"Failed to fetch Twilio ICE servers: {e}")

    # 4. Fallback to highly reliable public STUN/TURN servers
    return [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
        {"urls": ["stun:stun.relay.metered.ca:80"]},
        {
            "urls": ["turn:global.relay.metered.ca:80"],
            "username": "openrelayproject",
            "credential": "openrelayproject",
        },
        {
            "urls": ["turn:global.relay.metered.ca:443"],
            "username": "openrelayproject",
            "credential": "openrelayproject",
        },
    ]


def show():
    # Prototype Disclaimer
    st.info(
        """
**Prototype Disclaimer**  
This module demonstrates hand tracking and finger tapping visualization.  
Clinical prediction using finger tapping data has not yet been implemented.
"""
    )

    # Title
    st.title("Finger Tapping Assessment")

    # Instructions
    st.markdown(
        """
### Instructions
1. Place your hand in front of the webcam.
2. Repeatedly tap your thumb and index finger.
3. The test will automatically stop after the predefined duration.
"""
    )

    # Initialize Session States
    if "results" not in st.session_state:
        st.session_state.results = {}
    if "webrtc_playing" not in st.session_state:
        st.session_state.webrtc_playing = False
    if "capture_done" not in st.session_state:
        st.session_state.capture_done = False

    # Assessment trigger
    if not st.session_state.webrtc_playing and not st.session_state.capture_done:
        if st.button("Start Assessment"):
            st.session_state.webrtc_playing = True
            st.rerun()

    # WebRTC Streamer Block
    if st.session_state.webrtc_playing:
        ctx = webrtc_streamer(
            key="fingertap",
            mode=WebRtcMode.SENDRECV,
            desired_playing_state=True,
            video_processor_factory=FingerTapProcessor,
            media_stream_constraints={"video": True, "audio": False},
            rtc_configuration={"iceServers": get_ice_servers()},
        )

        # Main Thread Synchronization: The Correct Architecture
        if ctx.state.playing and ctx.video_processor:
            with st.spinner("Recording in progress... Please tap your fingers."):

                # Failsafe timeout to prevent permanent hanging if the camera fails to send frames
                timeout = 35
                start_wait = time.time()

                # We block the main Streamlit thread using a while loop.
                # This is the correct architecture because WebRTC frame processing
                # happens in an isolated background asyncio thread.
                # This prevents UI re-renders from killing the WebRTC socket.
                while not ctx.video_processor.finished:
                    if time.time() - start_wait > timeout:
                        st.error(
                            "Camera feed timed out. Please check your permissions or network connection."
                        )
                        st.stop()
                    time.sleep(0.5)

                # Once the background thread flags finished=True, extract data safely
                st.session_state.final_times = ctx.video_processor.times
                st.session_state.final_distances = ctx.video_processor.distances

                # Update states to trigger the finish screen and shut down camera
                st.session_state.webrtc_playing = False
                st.session_state.capture_done = True

                st.session_state.fingertap_completed = True
                st.session_state.results["fingertap"] = {"status": "Completed"}

                # We trigger EXACTLY ONE rerun here to turn off the camera and render the plot.
                st.rerun()

    # Results Block
    if st.session_state.capture_done:
        st.success("Assessment Complete")

        # Render graph directly inside Streamlit
        fig = generate_graph(
            st.session_state.final_times, st.session_state.final_distances
        )
        st.pyplot(fig)
