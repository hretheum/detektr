"""Setup configuration for frame-buffer-v2."""

from setuptools import find_packages, setup

setup(
    name="frame-buffer-v2",
    version="2.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
)
