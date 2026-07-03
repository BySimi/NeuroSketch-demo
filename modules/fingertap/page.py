import os
import time
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from modules.fingertap.detector import FingerTapProcessor, generate_graph


def get_ice_servers():
    """
    Returns ICE server configuration safely for Hugging Face Spaces and Streamlit Cloud.
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        local_secrets = os.path.join(os.getcwd(), ".streamlit", "secrets.toml")
        global_secrets = os.path.join(
            os.path.expanduser("~"), ".streamlit", "secrets.toml"
        )

        if os.path.exists(local_secrets) or os.path.exists(global_secrets):
            try:
                account_sid = st.secrets.get("TWILIO_ACCOUNT_SID")
                auth_token = st.secrets.get("TWILIO_AUTH_TOKEN")
            except Exception:
                pass

    if account_sid and auth_token:
        try:
            from twilio.rest import Client

            client = Client(account_sid, auth_token)
            token = client.tokens.create()
            return token.ice_servers
        except Exception as e:
            print(f"Failed to fetch Twilio ICE servers: {e}")

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

    # Initialize Strict State Machine
    if "results" not in st.session_state:
        st.session_state.results = {}
    if "webrtc_playing" not in st.session_state:
        st.session_state.webrtc_playing = False
    if "capture_finished" not in st.session_state:
        st.session_state.capture_finished = False
    if "capture_done" not in st.session_state:
        st.session_state.capture_done = False

    # 1. Start Assessment Button
    if (
        not st.session_state.webrtc_playing
        and not st.session_state.capture_finished
        and not st.session_state.capture_done
    ):
        if st.button("Start Assessment"):
            st.session_state.webrtc_playing = True
            st.rerun()

    # 2. WebRTC Streamer Block
    # The component MUST remain in the DOM until it completely finishes shutting down
    show_streamer = (
        st.session_state.webrtc_playing or st.session_state.capture_finished
    ) and not st.session_state.capture_done

    if show_streamer:
        # Camera runs ONLY if we are playing and haven't finished capturing
        desired_state = (
            st.session_state.webrtc_playing and not st.session_state.capture_finished
        )

        ctx = webrtc_streamer(
            key="fingertap_streamer",
            mode=WebRtcMode.SENDRECV,
            desired_playing_state=desired_state,
            video_processor_factory=FingerTapProcessor,
            media_stream_constraints={"video": True, "audio": False},
            rtc_configuration={"iceServers": get_ice_servers()},
        )

        # 3. Active Recording Synchronization
        if desired_state and ctx.state.playing and ctx.video_processor:
            status_placeholder = st.empty()
            status_placeholder.markdown(
                "### 🎥 Recording Active... Please tap your fingers."
            )

            # Pinned Polling Loop
            while ctx.state.playing and not ctx.video_processor.finished:
                time.sleep(0.2)

            # STEP 1: Extraction & Shutdown Signal
            if ctx.video_processor:
                # Capture data if 20 seconds elapsed OR the user manually stopped early
                if ctx.video_processor.finished or not ctx.state.playing:
                    st.session_state.final_times = ctx.video_processor.times
                    st.session_state.final_distances = ctx.video_processor.distances

                    # Signal that capture is done, which turns desired_state to False on the next run
                    st.session_state.capture_finished = True
                    status_placeholder.empty()
                    st.rerun()

        # STEP 2: Graceful Shutdown Handshake
        # We wait patiently for the React frontend to fully terminate the WebRTC connection
        if st.session_state.capture_finished and not ctx.state.playing:
            # Once confirmed dead, we trigger the final state change
            st.session_state.capture_done = True
            st.session_state.fingertap_completed = True
            st.session_state.results["fingertap"] = {"status": "Completed"}
            st.rerun()

    # 4. Final Results Block
    if st.session_state.capture_done:
        st.success("Assessment Complete")

        # Render graph natively inside Streamlit
        fig = generate_graph(
            st.session_state.final_times, st.session_state.final_distances
        )
        st.pyplot(fig)
