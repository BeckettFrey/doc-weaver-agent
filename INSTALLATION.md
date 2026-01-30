# Installation Guide

> [!IMPORTANT]
> Devices marked as **(Stable)** have been verified by multiple users. New installation instructions are added as devices are tested and confirmed compatible.

## Prerequisites

Before installing, ensure you have:

1. A supported device (see platform-specific instructions below)
2. [pipx](https://pipx.pypa.io/stable/) installed for isolated Python application management
3. Git installed on your system

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/beckettfrey/doc-weaver-agent.git
cd doc-weaver-agent
```

### 2. Platform-Specific Setup

<img src="https://raw.githubusercontent.com/marwin1991/profile-technology-icons/main/icons/macos.png" width="24" height="24" alt="macOS"> 

**macOS 26+ on Apple Silicon (ARM64) - Stable**

Tested with pipx 1.7.1
```bash
pipx install .
```

<img src="https://raw.githubusercontent.com/marwin1991/profile-technology-icons/main/icons/windows.png" width="24" height="24" alt="Windows">

**UNEXPLORED**

<img src="https://raw.githubusercontent.com/marwin1991/profile-technology-icons/main/icons/linux.png" width="24" height="24" alt="Linux"> 

**UNEXPLORED**

### 3. Verify Installation

Confirm the installation was successful:
```bash
doc-weaver --help
```

## Troubleshooting

If you encounter issues:
- Ensure pipx is properly installed and in your PATH
- Verify you're using a compatible Python version
- Check the [Issues](https://github.com/beckettfrey/doc-weaver-agent/issues) page for known problems

## Contributing

Successfully installed on an unlisted platform? I'd love to hear from you! Please open an issue or pull request with your installation steps.