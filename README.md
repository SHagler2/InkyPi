# InkyPi 

<img src="./docs/images/inky_clock.jpg" />


## About InkyPi 
InkyPi is an open-source, customizable E-Ink display powered by a Raspberry Pi. Designed for simplicity and flexibility, it allows you to effortlessly display the content you care about, with a simple web interface that makes setup and configuration effortless.

**Features**:
- Natural paper-like aethetic: crisp, minimalist visuals that are easy on the eyes, with no glare or backlight
- Web Interface allows you to update and configure the display from any device on your network
- Minimize distractions: no LEDS, noise, or notifications, just the content you care about
- Easy installation and configuration, perfect for beginners and makers alike
- Open source: distributed under the MIT license, allowing you to modify, customize, and create your own plugins

**Plugins**:

- Image Upload: Upload and display any image from your browser
- Newspaper: Show daily front pages of major newspapers from around the world
- Clock: Customizable clock faces for displaying time
- AI Image: Generate images from text prompts using ChatGPT's DALL·E

And additional plugins coming soon!

## Hardware

- Raspberry Pi (4 | 3 | Zero 2 W | Zero W)
    - Recommended to get 40 pin Pre Soldered Header
- MicroSD Card (min 8 GB)
- E-Ink Display: Pimoroni Inky Impression, available in 3 sizes:
    - **[4 Inch Display](https://shop.pimoroni.com/products/inky-impression-4)**
    - **[5.7 Inch Display](https://shop.pimoroni.com/products/inky-impression-5-7)**
    - **[7.3 Inch Display](https://shop.pimoroni.com/products/inky-impression-7-3)**
- Picture Frame or 3D Stand

## Installation
To install InkyPi, follow these steps:

1. Clone the repository:
    ```bash
    git clone https://github.com/fatihak/InkyPi.git
    ```
2. Navigate to the project directory:
    ```bash
    cd InkyPi
    ```
3. Run the installation script with sudo:
    ```bash
    sudo bash install/install.sh
    ```

After the installation is complete, the script will prompt you to reboot your Raspberry Pi. Once rebooted, the display will update to show the InkyPi splash screen.

Note: 
- The installation script requires sudo privileges to install and run the service. We recommend starting with a fresh installation of Raspberry Pi OS to avoid potential conflicts with existing software or configurations.
- The installation process will automatically enable the required SPI and I²C interfaces on your Raspberry Pi.

## Uninstall
To install InkyPi, simply run the following command:

```bash
sudo bash install/uninstall.sh
```

## License

Distributed under the MIT License, see [LICENSE](./LICENSE) for more information.

## Issues

Check out the [troubleshooting guide](./docs/Troubleshooting.md). If you're still having trouble, feel free to create an issue on the [GitHub Issues](https://github.com/fatihak/InkyPi/issues) page.