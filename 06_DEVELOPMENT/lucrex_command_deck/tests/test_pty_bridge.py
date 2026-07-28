import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pty_bridge as pb


class TestWS(unittest.TestCase):
    def test_accept_key_rfc_example(self):
        # RFC 6455 section 1.3 canonical example.
        self.assertEqual(pb.accept_key("dGhlIHNhbXBsZSBub25jZQ=="),
                         "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    def test_roundtrip_masked_client_frame(self):
        payload = b"hello lucrex"
        frame = pb.mask_frame(payload, opcode=0x1)
        msgs, leftover = pb.decode_frames(frame)
        self.assertEqual(leftover, b"")
        self.assertEqual(msgs, [(0x1, payload)])

    def test_server_frame_is_unmasked(self):
        payload = b"x" * 200  # forces the 2-byte length path
        frame = pb.encode_frame(payload, opcode=0x2)
        self.assertEqual(frame[0] & 0x0f, 0x2)
        self.assertEqual(frame[1] & 0x80, 0)  # server never masks

    def test_two_frames_in_one_buffer(self):
        f = pb.mask_frame(b"aa") + pb.mask_frame(b"bb")
        msgs, leftover = pb.decode_frames(f)
        self.assertEqual(leftover, b"")
        self.assertEqual(msgs, [(0x1, b"aa"), (0x1, b"bb")])

    def test_partial_frame_returns_leftover(self):
        frame = pb.mask_frame(b"partial-data-here")
        msgs, leftover = pb.decode_frames(frame[:5])
        self.assertEqual(msgs, [])
        self.assertEqual(leftover, frame[:5])


if __name__ == "__main__":
    unittest.main()
