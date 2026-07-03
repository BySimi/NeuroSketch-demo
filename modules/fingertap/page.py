import os
import time
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from modules.fingertap.detector import FingerTapProcessor, generate_graph


def get_ice_servers():
    """
    Returns ICE server configuration safely for Hugging Face Spaces and Streamlit Cloud.
    """
    account_sid = None
    auth_token = None

    # 1. Safely check OS environment variables (Hugging Face standard)
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

    # 2. If OS env vars aren't set, check for a local Streamlit secrets file
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

    # 3. If credentials are found, fetch Twilio ICE servers
    if account_sid and auth_token:
        try:
            from twilio.rest import Client

            client = Client(account_sid, auth_token)
            token = client.tokens.create()
            return token.ice_servers
        except Exception as e:
            print(f"Failed to fetch Twilio ICE servers: {e}")

    # 4. Fallback to reliable public STUN/TURN servers
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
            key="fingertap_streamer",
            mode=WebRtcMode.SENDRECV,
            desired_playing_state=True,
            video_processor_factory=FingerTapProcessor,
            media_stream_constraints={"video": True, "audio": False},
            rtc_configuration={"iceServers": get_ice_servers()},
        )

        # Main Thread Synchronization: Stabilized Thread-Pinning
        # This execution block triggers ONLY when the connection is established and active
        if ctx.state.playing and ctx.video_processor:
            status_placeholder = st.empty()
            status_placeholder.markdown(
                "### 🎥 Recording Active... Please tap your fingers."
            )

            # Pinned Polling Loop: Safely sleep without calling st.rerun() continuously.
            # This protects the WebSocket connection from dropping and breaking session state.
            while ctx.state.playing and not ctx.video_processor.finished:
                time.sleep(0.2)

            # Once the 20 seconds finish or the stream stops, extract the data securely
            if ctx.video_processor and ctx.video_processor.finished:
                st.session_state.final_times = ctx.video_processor.times
                st.session_state.final_distances = ctx.video_processor.distances

                # Update states to close the camera and switch to the results layout
                st.session_state.webrtc_playing = False
                st.session_state.capture_done = True

                st.session_state.fingertap_completed = True
                st.session_state.results["fingertap"] = {"status": "Completed"}

                # Clear the status indicator and trigger exactly ONE clean rerun to load results
                status_placeholder.empty()
                st.rerun()

    # Results Block
    if st.session_state.capture_done:
        st.success("Assessment Complete")

        # Render graph natively inside Streamlit
        fig = generate_graph(
            st.session_state.final_times, st.session_state.final_distances
        )
        st.pyplot(fig)
import os
import time
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from modules.fingertap.detector import FingerTapProcessor, generate_graph

def get_ice_servers():
    """
    Returns ICE server configuration safely for Hugging Face Spaces and Streamlit Cloud.
    """
    account_sid = None
    auth_token = None

    # 1. Safely check OS environment variables (Hugging Face standard)
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

    # 2. If OS env vars aren't set, check for a local Streamlit secrets file
    if not account_sid or not auth_token:
        local_secrets = os.path.join(os.getcwd(), ".streamlit", "secrets.toml")
        global_secrets = os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml")
        
        if os.path.exists(local_secrets) or os.path.exists(global_secrets):
            try:
                account_sid = st.secrets.get("TWILIO_ACCOUNT_SID")
                auth_token = st.secrets.get("TWILIO_AUTH_TOKEN")
            except Exception:
                pass

    # 3. If credentials are found, fetch Twilio ICE servers
    if account_sid and auth_token:
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            token = client.tokens.create()
            return token.ice_servers
        except Exception as e:
            print(f"Failed to fetch Twilio ICE servers: {e}")

    # 4. Fallback to reliable public STUN/TURN servers
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
    
    # New state to handle the two-step shutdown process safely
    if "data_saved" not in st.session_state:
        st.session_state.data_saved = False

    # Assessment trigger
    if not st.session_state.webrtc_playing and not st.session_state.data_saved and not st.session_state.capture_done:
        if st.button("Start Assessment"):
            st.session_state.webrtc_playing = True
            st.rerun()

    # WebRTC Streamer Block
    # We now keep the component rendered EVEN IF we are shutting it down, 
    # to prevent the "NoneType" thread crash. It only vanishes when capture_done is True.
    if st.session_state.webrtc_playing or (st.session_state.data_saved and not st.session_state.capture_done):
        
        ctx = webrtc_streamer(
            key="fingertap_streamer",
            mode=WebRtcMode.SENDRECV,
            desired_playing_state=st.session_state.webrtc_playing,
            video_processor_factory=FingerTapProcessor,
            media_stream_constraints={"video": True, "audio": False},
            rtc_configuration={"iceServers": get_ice_servers()},
        )

        # Main Thread Synchronization: Active Recording
        if ctx.state.playing and ctx.video_processor:
            status_placeholder = st.empty()
            status_placeholder.markdown("### 🎥 Recording Active... Please tap your fingers.")
            
            # Pinned Polling Loop
            while ctx.state.playing and not ctx.video_processor.finished:
                time.sleep(0.2)

            # STEP 1: Once finished, extract data and initiate GRACEFUL SHUTDOWN
            if ctx.video_processor and ctx.video_processor.finished:
                st.session_state.final_times = ctx.video_processor.times
                st.session_state.final_distances = ctx.video_processor.distances
                
                # We turn the camera off, but DO NOT declare capture_done yet.
                st.session_state.data_saved = True
                st.session_state.webrtc_playing = False 
                
                status_placeholder.empty()
                st.rerun()

        # STEP 2: Wait for the streamer to fully stop its background threads.
        # Once ctx.state.playing is completely False, it is safe to remove it from the page.
        if st.session_state.data_saved and not ctx.state.playing:
            st.session_state.capture_done = True
            st.session_state.fingertap_completed = True
            st.session_state.results["fingertap"] = {"status": "Completed"}
            st.rerun()

    # Results Block
    if st.session_state.capture_done:
        st.success("Assessment Complete")

        # Render graph natively inside Streamlit
        fig = generate_graph(
            st.session_state.final_times, st.session_state.final_distances
        )
        st.pyplot(fig)