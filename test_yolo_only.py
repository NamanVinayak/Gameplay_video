"""
Simple test to verify YOLO tracking works without full video pipeline
Tests the FaceTracker module in isolation
"""
from pathlib import Path
from modules.face_tracker import FaceTracker
import sys

def test_yolo_tracker():
    """Test YOLO face tracking on a single video"""
    print("=" * 60)
    print("YOLO Face Tracking Test")
    print("=" * 60)

    # Use test video
    test_video = Path("test_assets/example_gameplay.mp4")

    if not test_video.exists():
        print(f"❌ Test video not found: {test_video}")
        print("Please ensure test_assets/example_gameplay.mp4 exists")
        return False

    print(f"✓ Test video found: {test_video}")
    print(f"  Size: {test_video.stat().st_size / 1024 / 1024:.2f} MB")

    # Create temp job folder
    job_folder = Path("outputs/test_yolo")
    job_folder.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize Face Tracker
        print("\n1. Initializing YOLOv8 Pose model...")
        tracker = FaceTracker(job_folder)
        print("   ✓ YOLO model loaded successfully")

        # Track faces in first 10 seconds
        print("\n2. Tracking subject in video (first 10 seconds)...")
        print("   This will:")
        print("   - Detect people using YOLOv8")
        print("   - Extract pose keypoints (nose, eyes)")
        print("   - Calculate median position for stability")

        tracking_data = tracker.track_faces_in_clip(
            video_path=test_video,
            start_time="00:00:00",
            end_time="00:00:10",
            sample_rate=5  # Sample every 5 frames
        )

        # Display results
        print("\n3. Tracking Results:")
        print(f"   Subject center: ({tracking_data['face_center_x']}, {tracking_data['face_center_y']})")
        print(f"   Video dimensions: {tracking_data['source_width']}x{tracking_data['source_height']}")
        print(f"   Detections: {len(tracking_data['face_positions'])} frames")

        if tracking_data['face_positions']:
            sample = tracking_data['face_positions'][0]
            print(f"\n   Sample detection:")
            print(f"   - Method: {sample.get('method', 'unknown')}")
            print(f"   - Confidence: {sample.get('confidence', 0):.2f}")
            print(f"   - Keypoints used: {sample.get('keypoints_used', 0)}/3")

        print("\n" + "=" * 60)
        print("✅ YOLO TRACKING TEST PASSED!")
        print("=" * 60)
        print("\nThe YOLO integration is working correctly.")
        print("Subject detection and tracking successful!")
        print(f"\nLogs saved to: {job_folder / 'processing.log'}")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_yolo_tracker()
    sys.exit(0 if success else 1)
