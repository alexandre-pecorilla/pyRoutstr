# pyRoutstr v1.0

A GUI client for Routstr - Access the best proprietary and open-source AI models with Bitcoin payments.

✨ **Nothing beats reality** ✨

## Features

- ⚡ **Pay-per-use** - Lightning & Cashu, pay only for what you use
- 🔐 **Zero KYC** - Private signup via Nostr, keep your identity hidden
- 🌐 **Decentralized** - Independent providers, no central control
- 🕵️ **Anonymous** - Tor integration masks your IP

## Complete Installation Guide

### Linux (Ubuntu/Debian)

#### 1. Install Python 3 and required system packages

```bash
# Update package list
sudo apt update

# Install Python 3, pip, venv, and Tkinter
sudo apt install python3 python3-pip python3-venv python3-tk git
```

#### 2. Clone the repository

```bash
git clone https://github.com/alexandre-pecorilla/pyRoutstr.git
cd pyRoutstr
```

#### 3. Create and activate virtual environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

#### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

#### 5. Run pyRoutstr

```bash
python pyroutstr.py
```

#### 6. (Optional) Install Tor for anonymous routing

```bash
sudo apt install tor
# Tor will run on localhost:9050 by default
```

### macOS

#### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Python 3, Git and Tkinter

```bash
# Install Python 3 (includes pip)
brew install python

# Install Tkinter
brew install python-tk

# Install Git (if not already installed)
brew install git
```

#### 3. Clone the repository

```bash
git clone https://github.com/alexandre-pecorilla/pyRoutstr.git
cd pyRoutstr
```

#### 4. Create and activate virtual environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

#### 5. Install Python dependencies

```bash
pip install -r requirements.txt
```

#### 6. Run pyRoutstr

```bash
python pyroutstr.py
```

#### 7. (Optional) Install Tor for anonymous routing

```bash
brew install tor
# Start Tor service
brew services start tor
# Tor will run on localhost:9050
```

### Linux (Fedora/RHEL/CentOS)

#### 1. Install Python 3 and required system packages

```bash
# Install Python 3, pip, and Tkinter
sudo dnf install python3 python3-pip python3-tkinter git
```

#### 2. Follow steps 2-6 from the Ubuntu/Debian instructions above

## Usage

1. **First Run**: On first launch, go to **File → Settings** to configure your API key
2. **Get API Key**: Sign up at [https://chat.routstr.com](https://chat.routstr.com) and create an API key
3. **Start Chatting**: Click **File → New Conversation**, select a model, and start chatting!

## Troubleshooting

### "No module named 'tkinter'" error

**Linux**: Install python3-tk package (see installation instructions above)

**macOS**: Install python-tk using Homebrew (see installation instructions above)

### Tor connection issues

Ensure Tor is running on `localhost:9050`. You can verify with:
```bash
curl --socks5 localhost:9050 https://check.torproject.org/
```

## Requirements

- Python 3.8+
- Tkinter (GUI framework)
- Internet connection
- Routstr API key
- Tor (optional, for anonymous routing)

## Author

**Alex Pecorilla**  
Nostr: `npub1t9ak286ttdxf0njjf8nmvazhyvxx72xeazx7n2udcg0h5dy7e68sl8dw5g`

## License

[Add your license here]

---

*Vibe-coded with Claude Opus 4*
