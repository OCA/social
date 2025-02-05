from base64 import b64encode
from io import BytesIO

from PIL import Image

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestResUsersDigitalSignature(SavepointCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_model = cls.env["res.users"]

        # Create a test user
        cls.user = cls.user_model.create(
            {
                "name": "Test User",
                "login": "test_user",
                "email": "test_user@example.com",
            }
        )

    def _generate_sample_image(self):
        """Generate a small valid image and return its base64-encoded content."""
        img = Image.new("RGB", (10, 10), color="red")  # Create a red 10x10 image
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return b64encode(buffer.getvalue()).decode("ascii")

    def test_digital_signature_field(self):
        """Test assigning and clearing the digital signature field."""
        # Generate a valid base64-encoded image
        test_signature = self._generate_sample_image()

        # Assign a digital signature to the user
        self.user.digital_signature = test_signature
        self.assertEqual(
            self.user.digital_signature.decode("ascii"),
            test_signature,
            "Digital signature should be set correctly.",
        )

        # Clear the digital signature using the method
        self.user.clear_digital_signature()
        self.assertFalse(
            self.user.digital_signature, "Digital signature should be cleared."
        )

    def test_self_readable_fields(self):
        """Test if 'digital_signature' is included in SELF_READABLE_FIELDS."""
        readable_fields = self.user.SELF_READABLE_FIELDS
        self.assertIn(
            "digital_signature",
            readable_fields,
            "'digital_signature' should be in SELF_READABLE_FIELDS.",
        )

    def test_self_writeable_fields(self):
        """Test if 'digital_signature' is included in SELF_WRITEABLE_FIELDS."""
        writeable_fields = self.user.SELF_WRITEABLE_FIELDS
        self.assertIn(
            "digital_signature",
            writeable_fields,
            "'digital_signature' should be in SELF_WRITEABLE_FIELDS.",
        )
