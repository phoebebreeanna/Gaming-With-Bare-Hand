ICON_MAC = assets/logo/hand_gesture_icon.icns
ICON_WIN = assets/logo/hand_gesture_icon.ico
ICON_PNG = assets/logo/hand_gesture_icon.png
ICONSET_DIR = assets/logo/hand_gesture_icon.iconset

icon-win: $(ICON_PNG)
	python -c "from PIL import Image; img = Image.open('$(ICON_PNG)'); img.save('$(ICON_WIN)', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"

icon-mac: $(ICON_PNG)
	mkdir -p "$(ICONSET_DIR)"
	sips -z 16 16     "$(ICON_PNG)" --out "$(ICONSET_DIR)/icon_16x16.png"
	sips -z 32 32     "$(ICON_PNG)" --out "$(ICONSET_DIR)/icon_16x16@2x.png"
	sips -z 32 32     "$(ICON_PNG)" --out "$(ICONSET_DIR)/icon_32x32.png"
	sips -z 64 64     "$(ICON_PNG)" --out "$(ICONSET_DIR)/icon_32x32@2x.png"
	sips -z 128 128   "$(ICON_PNG)" --out "$(ICONSET_DIR)/icon_128x128.png"
	sips -z 256 256   "$(ICON_PNG)" --out "$(ICONSET_DIR)/icon_128x128@2x.png"
	sips -z 256 256   "$(ICON_PNG)" --out "$(ICONSET_DIR)/icon_256x256.png"
	sips -z 512 512   "$(ICON_PNG)" --out "$(ICONSET_DIR)/icon_256x256@2x.png"
	sips -z 512 512   "$(ICON_PNG)" --out "$(ICONSET_DIR)/icon_512x512.png"
	sips -z 1024 1024 "$(ICON_PNG)" --out "$(ICONSET_DIR)/icon_512x512@2x.png"
	iconutil -c icns "$(ICONSET_DIR)" -o "$(ICON_MAC)"
	rm -rf "$(ICONSET_DIR)"

DMG_NAME = HandMouse.dmg
APP_NAME = HandMouse

run:
	python main.py

build-mac-app:
	pyinstaller main.spec --noconfirm
	/usr/libexec/PlistBuddy -c \
		"Add :NSCameraUsageDescription string 'HandMouse uses the camera to detect hand gestures for mouse control.'" \
		dist/HandMouse.app/Contents/Info.plist
	codesign --force --deep --sign - dist/HandMouse.app

build-mac-dmg: build-mac-app
	rm -f "dist/$(DMG_NAME)"
	create-dmg \
		--volname "$(APP_NAME)" \
		--window-size 500 320 \
		--icon-size 100 \
		--icon "HandMouse.app" 130 120 \
		--app-drop-link 370 120 \
		"dist/$(DMG_NAME)" \
		"dist/HandMouse.app"

build-win:
	pyinstaller main.py --noconsole --onedir \
		--icon="$(ICON_WIN)" \
		--add-data="assets;assets" \
		--add-data="logic/data;logic/data" \
		--add-data="logic/conf;logic/conf" \
		--add-data="logic/chatbot/data;logic/chatbot/data" \
		--add-data="logic/chatbot/chroma_db;logic/chatbot/chroma_db" \
		--add-data="hockey_game;hockey_game" \
		--hidden-import=pygame \
		--hidden-import=logic.gesture_pipeline \
		--hidden-import=tiktoken_ext.openai_public \
		--hidden-import=tiktoken_ext \
		--collect-all numpy \
		--collect-all cv2 \
		--collect-all mediapipe \
		--collect-all scipy \
		--collect-all sklearn \
		--collect-all torch \
		--collect-all pygame \
		--collect-all chromadb \
		--collect-all llama_cpp \
		--collect-all llama_index \
		--collect-all transformers \
		--collect-all tokenizers \
		--collect-all huggingface_hub \
		--collect-all sentence_transformers \
		--collect-all certifi \
		--collect-all openai \
		--collect-all httpx \
		--collect-all httpcore \
		--collect-all tiktoken

ISCC ?= "C:/Program Files (x86)/Inno Setup 6/ISCC.exe"

build-win-installer: build-win
	$(ISCC) installer.iss

eval:
	cd research && python evaluate.py dataset

clean:
	rm -rf build dist
