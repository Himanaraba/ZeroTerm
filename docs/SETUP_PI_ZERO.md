# Setup: Raspberry Pi Zero 2 W (Kali Lite)

This guide assumes a headless Kali Linux Lite image on Raspberry Pi Zero 2 W
and systemd as the init system.

## 1) Flash the OS
- Download the Kali Linux ARM image for Raspberry Pi Zero 2 W.
- Flash it to a microSD card.

## 2) Headless bootstrap (no HDMI)
On the boot partition:
- Create an empty file named `ssh` to enable SSH on first boot.
- Create `wpa_supplicant.conf` with your Wi-Fi credentials.

Example `wpa_supplicant.conf`:
```
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
  ssid="YOUR_SSID"
  psk="YOUR_PASSWORD"
  key_mgmt=WPA-PSK
}
```

## 3) First boot
- Power on the Pi and connect over SSH.
- Change default passwords and update packages.

## 4) Install dependencies
```
sudo apt update
sudo apt install -y python3 git
```

## 5) Deploy the repo
```
sudo mkdir -p /opt/zeroterm
sudo git clone <your-repo-url> /opt/zeroterm
```

## 6) Decide runtime user

ZeroTerm assumes a full-power shell. Running as root preserves unrestricted
command access (default). If you choose a dedicated user, some commands will
be unavailable and that conflicts with the project goals.

## 7) Configure
```
sudo mkdir -p /etc/zeroterm
sudo cp /opt/zeroterm/config/zeroterm.env /etc/zeroterm/zeroterm.env
sudo nano /etc/zeroterm/zeroterm.env
```

## 8) Install and enable systemd service
```
sudo cp /opt/zeroterm/systemd/zeroterm.service /etc/systemd/system/zeroterm.service
sudo systemctl daemon-reload
sudo systemctl enable --now zeroterm.service
```

## 9) Access from iPad
- Connect the iPad to the Pi management Wi-Fi network.
- Open `http://<pi-ip>:<port>/` in Safari.

## Notes
- Built-in Wi-Fi is for management/web access.
- Use an external USB Wi-Fi adapter for monitoring or experiments.
- The web UI is a terminal cable. No GUI or command restrictions are added.
