from setuptools import setup, find_packages

setup(
    name="twc-core",
    version="0.1.0",
    description="Unified ML Infrastructure for Federated Learning Projects",
    author="TA (XJTLU)",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.24",
        "torch>=2.0",
        "torchvision>=0.15",
        "pillow>=9.0",
        "pandas>=1.5",
    ],
    extras_require={
        "yolo": ["ultralytics>=8.0"],
        "all": ["ultralytics>=8.0"],
    },
)
