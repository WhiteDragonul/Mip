🤖 MIP — Your Desktop Robot Companion

MIP is an EMO-inspired digital pet that lives on your computer.

MIP watches you through the webcam, listens to your voice, talks back with a cute robotic personality, and expresses emotions through animated eyes and facial expressions.

The project is designed as a digital prototype for a future Raspberry Pi robot.

✨ Features
👀 Animated cyan eyes
😊 Multiple emotions and facial expressions
🎤 Voice conversations
📷 Face tracking with the webcam
🧠 AI-powered personality
🔊 Cute robotic voice
💬 Short and friendly replies
🖥️ Runs as a desktop companion
🍓 Designed for future Raspberry Pi hardware
🎭 Emotions

MIP can express:

Happy
Sad
Angry
Curious
Surprised
Sleepy
Neutral
📸 How It Works
The webcam detects your face.
MIP follows you with its eyes.
The microphone listens to your voice.
The AI generates a response.
MIP speaks using a robotic voice.
The face animates according to the emotion.
🚀 Installation
pip install -r requirements.txt

Run MIP:

python main.py

Press ESC to quit.

📁 Project Structure
main.py

mip/
├── app.py
├── config.py
├── state.py
│
├── hardware/
├── face/
├── perception/
└── brain/
🧵 Architecture
Main thread → face animation
Camera thread → face tracking
Voice thread → speech interaction

All modules share the same robot state.

🍓 Raspberry Pi Ready

The project uses a hardware abstraction layer, making it easy to replace:

Laptop display → SPI display
Webcam → Pi Camera
Speakers and microphone → USB audio devices

Most of the code can be reused without modification.

🔮 Future Plans
Physical movement
Wheel motors
Pan/tilt head
Distance sensors
Edge detection
Autonomous behaviors
❤️ MIP

A digital companion today.

A real robot tomorrow.
