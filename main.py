import cv2
print(cv2.getBuildInformation())

# # Receive the MPEG-TS UDP stream sent from the Raspberry Pi
# pipeline = (
#     "udpsrc port=6000 ! "
#     "application/x-mpegts ! "
#     "tsdemux ! "
#     "h264parse ! "
#     "avdec_h264 ! "
#     "videoconvert ! "
#     "appsink"
# )

# cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

# if not cap.isOpened():
#     print("Failed to open stream")
#     exit()

# while True:
#     ret, frame = cap.read()
#     if not ret:
#         print("No frame received")
#         break

#     cv2.imshow("Camera", frame)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# cap.release()
# cv2.destroyAllWindows()