# Mattermost-Tools
Mattermost tools developed with Mattermost API and mattermostdriver

## Components
- mattermost-auto-reply: Auto reply message on certain circumstances.

### mattermost-auto-reply
#### How to run

- **Use python to run:** `python3 auto_reply_tool.py`, notice you need some python packeges to run and only python3 supported.
- **Run binary:** Download the binary from  [release page](https://github.com/Martzki/Mattermost-Tools/releases) and run directly. Then we will create a GUI tray icon so you can click to visit the web console or exit using it. Notice only win32 platform support the GUI binary.

#### Commandline options

There are few options supplied to run with:

``` bash
usage: auto_reply_tool.py [-h] [--debug] [--address ADDRESS] [--port PORT]

optional arguments:
  -h, --help         show this help message and exit
  --debug            Enable debug mode.
  --address ADDRESS  Listen on this address. Default: 127.0.0.1.
  --port PORT        Listen on this port. Default: 6655.

```

`--debug`: This option will set log level to DEBUG when logging to file. Log level in stderr in always INFO.

`--address`: This option can set the address to listen on. `127.0.0.1`is a good choice on most occasions, and for security you shouldn't change it unless necessary.

`--port`: This option can set the port to listen on. If the default port is already used by other process, use this to change the port.

#### Login and set auto reply config

Use your web browser to visit: `http://127.0.0.1:6655`(By default, if you haven't change the address and port).

Then login with your authentication and change your config on the web page directly.

#### Auto reply config

There are some config you can change when using auto reply:

`Reply Interval`: If the interval between the last two message received in the same channel is larger than interval, then send a reply message.

`Max Interval`: Extend next auto reply interval to this value(only accept seconds now).

`Reply Message`: The message to send. You can wrap on the textarea and don't need to use `\n` yourself.

`Extend Message`: When this message is received, the next auto reply interval of this channel is set to `Max Interval`.

