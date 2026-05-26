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

run:
	python main.py

build-mac:
	pyinstaller main.py --noconsole --onedir --windowed --noconfirm \
		--icon="$(ICON_MAC)" \
		--add-data="assets:assets" \
		--add-data="logic/data:logic/data" \
		--add-data="logic/conf:logic/conf" \
		--collect-all numpy \
		--collect-all cv2 \
		--collect-all mediapipe \
		--collect-all scipy \
		--collect-all sklearn \
		--exclude-module libiconv
	/usr/libexec/PlistBuddy -c \
		"Add :NSCameraUsageDescription string 'HandMouse uses the camera to detect hand gestures for mouse control.'" \
		dist/main.app/Contents/Info.plist
	codesign --force --deep --sign - dist/main.app

build-win:
	pyinstaller main.py --noconsole --onedir \
		--icon="$(ICON_WIN)" \
		--add-data="assets;assets" \
		--add-data="logic/data;logic/data" \
		--add-data="logic/conf;logic/conf" \
		--collect-all numpy \
		--collect-all cv2 \
		--collect-all mediapipe \
		--collect-all scipy \
		--collect-all sklearn

eval:
	cd research && python evaluate.py dataset

clean:
	rm -rf build dist *.spec
