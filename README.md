## Setup

- in main.py, make sure to replace `add-deepgram-api-key` and `add-discord-bot-token` with your tokens.
- if on Mac, keep line 17 and update the path to your homebrew's installation of opus 
- create a venv and install the requirements
- in the created venv folder look for the file called `voice_client.py` and replace the `strip_header_ext` method with:

```python
@staticmethod
def strip_header_ext(self, data):
    import logging
    logger = logging.getLogger(__name__)
    try:
        if data[0] == 0xBE and data[1] == 0xDE and len(data) > 4:
            _, length = struct.unpack_from(">HH", data)
            offset = 4 + length * 4
            data = data[offset:]
    except IndexError as e:
        logger.warning(f"The IndexError occurred but we will ignore it! Just means this part of the data probably is 0 bytes.. Data: {data}")
    return data
```

Needed as a workaround for a known problem in the discord library when reading audio 0 audio bytes (i.e. noone is speaking). 