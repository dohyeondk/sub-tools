import os

from sub_tools.system.file import ensure_output_directory


class TestEnsureOutputDirectory:
    """Tests for ensure_output_directory function."""

    def test_creates_output_directory(self, tmp_path):
        """Test that output directory is created."""
        output_path = tmp_path / "output"
        ensure_output_directory(str(output_path))
        assert output_path.exists()
        assert output_path.is_dir()

    def test_does_not_fail_if_exists(self, tmp_path):
        """Test that function doesn't fail if directory already exists."""
        output_path = tmp_path / "output"
        os.makedirs(output_path)
        ensure_output_directory(str(output_path))  # Should not raise
        assert output_path.exists()
