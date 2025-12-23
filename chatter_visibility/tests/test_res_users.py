from odoo.tests.common import TransactionCase, new_test_user, tagged, users


@tagged("-at_install", "post_install")
class TestResUsers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_show_chatter = new_test_user(
            cls.env,
            login="test_show_user",
            name="Test User Show Chatter",
            email="test_show@example.com",
            groups="base.group_user",
        )
        cls.user_show_chatter.chatter_visibility = "show"

        cls.user_hide_chatter = new_test_user(
            cls.env,
            login="test_hide_user",
            name="Test User Hide Chatter",
            email="test_hide@example.com",
            groups="base.group_user",
        )
        cls.user_hide_chatter.chatter_visibility = "hide"

        cls.user_default_chatter = new_test_user(
            cls.env,
            login="test_default_user",
            name="Test User Default Chatter",
            email="test_default@example.com",
            groups="base.group_user",
        )

    def test_00_chatter_visibility_field_default_value(self):
        """Test that the chatter_visibility field has the correct default value."""
        self.assertEqual(
            self.user_default_chatter.chatter_visibility,
            "show",
            "Default chatter visibility should be 'show'",
        )

    def test_01_chatter_visibility_field_values(self):
        """Test that the chatter_visibility field accepts valid selection values."""
        self.assertEqual(
            self.user_show_chatter.chatter_visibility,
            "show",
            "Chatter visibility should be 'show'",
        )

        self.assertEqual(
            self.user_hide_chatter.chatter_visibility,
            "hide",
            "Chatter visibility should be 'hide'",
        )

    @users("test_show_user")
    def test_02_get_chatter_visibility_show_chatter(self):
        """Test get_chatter_visibility returns show chatter True for 'show' "
        "preference."""
        self.env.user.chatter_visibility = "show"

        result = self.env["res.users"].get_chatter_visibility()
        expected_result = {"show_chatter": True}

        self.assertEqual(
            result,
            expected_result,
            "Should return show chatter True for 'show' preference",
        )

    @users("test_hide_user")
    def test_03_get_chatter_visibility_hide_chatter(self):
        """Test get_chatter_visibility returns hide chatter True for 'hide'
        preference."""
        self.env.user.chatter_visibility = "hide"

        result = self.env["res.users"].get_chatter_visibility()
        expected_result = {"show_chatter": False}

        self.assertEqual(
            result,
            expected_result,
            "Should return show chatter False for 'hide' preference",
        )

    @users("test_default_user")
    def test_04_get_chatter_visibility_default_user(self):
        """Test get_chatter_visibility returns show chatter True for default
        user."""
        result = self.env["res.users"].get_chatter_visibility()
        expected_result = {"show_chatter": True}

        self.assertEqual(
            result,
            expected_result,
            "Should return show chatter True for default user preference",
        )

    @users("test_show_user")
    def test_05_chatter_visibility_update(self):
        """Test updating chatter_visibility field and its effect on
        get_chatter_visibility."""
        self.env.user.chatter_visibility = "show"
        result = self.env["res.users"].get_chatter_visibility()
        self.assertEqual(
            result,
            {"show_chatter": True},
            "Show preference should return show chatter True",
        )

        self.env.user.chatter_visibility = "hide"
        result = self.env["res.users"].get_chatter_visibility()
        self.assertEqual(
            result,
            {"show_chatter": False},
            "Hide preference should return show chatter False",
        )

        self.env.user.chatter_visibility = "show"
        result = self.env["res.users"].get_chatter_visibility()
        self.assertEqual(
            result,
            {"show_chatter": True},
            "Updated show preference should return show chatter True",
        )

    def test_06_multiple_users_different_preferences(self):
        """Test that different users can have different chatter visibility
        preferences."""
        show_result = self.user_show_chatter.with_user(
            self.user_show_chatter
        ).get_chatter_visibility()
        self.assertEqual(
            show_result,
            {"show_chatter": True},
            "Show user should return show chatter True",
        )

        hide_result = self.user_hide_chatter.with_user(
            self.user_hide_chatter
        ).get_chatter_visibility()
        self.assertEqual(
            hide_result,
            {"show_chatter": False},
            "Hide user should return show chatter False",
        )

        self.assertNotEqual(
            show_result,
            hide_result,
            "Users with different preferences should return different results",
        )

    def test_07_user_self_readable_writable_fields(self):
        """Test that users can read and write their own default chatter visibility
        field."""
        user_fields = self.user_show_chatter.with_user(self.user_show_chatter)

        readable_fields = user_fields.SELF_READABLE_FIELDS
        self.assertIn(
            "chatter_visibility",
            readable_fields,
            "chatter visibility should be in SELF_READABLE_FIELDS",
        )
        writeable_fields = user_fields.SELF_WRITEABLE_FIELDS
        self.assertIn(
            "chatter_visibility",
            writeable_fields,
            "chatter visibility should be in SELF_WRITEABLE_FIELDS",
        )

    @users("test_show_user")
    def test_08_chatter_visibility_with_user_context(self):
        """Test chatter visibility preference with proper user context."""
        res_users_model = self.env["res.users"]
        self.env.user.chatter_visibility = "show"
        result = res_users_model.get_chatter_visibility()
        self.assertEqual(
            result,
            {"show_chatter": True},
            "Show preference with user context should work",
        )

        self.env.user.chatter_visibility = "hide"
        result = res_users_model.get_chatter_visibility()
        self.assertEqual(
            result,
            {"show_chatter": False},
            "Hide preference with user context should work",
        )

    def test_09_chatter_visibility_method_consistency(self):
        """Test that get_chatter_visibility method returns consistent results."""
        user = self.user_show_chatter
        first_result = user.with_user(user).get_chatter_visibility()
        second_result = user.with_user(user).get_chatter_visibility()

        self.assertEqual(
            first_result,
            second_result,
            "Method should return consistent results",
        )

        user.chatter_visibility = "hide"
        changed_result = user.with_user(user).get_chatter_visibility()
        self.assertEqual(
            changed_result,
            {"show_chatter": False},
            "Hide preference should return show chatter False",
        )
        self.assertNotEqual(
            first_result,
            changed_result,
            "Preference update should return different result",
        )
