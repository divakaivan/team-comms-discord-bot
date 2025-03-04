import discord
from deepgram import DeepgramClient, PrerecordedOptions

bot = discord.Bot()
connections = {}

deepgram = DeepgramClient("add-deepgram-api-key")

options = PrerecordedOptions(
    model="nova-3",
    smart_format=True,
    utterances=True,
    punctuate=True,
)

# needed only for unix-based systems apparently
discord.opus.load_opus("/opt/homebrew/Cellar/opus/1.5.2/lib/libopus.0.dylib")

import time
# Update your connections dict to store both the vc and start time.

@bot.command()
async def record(ctx):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("⚠️ You aren't in a voice channel!")
        return
    vc = await voice.channel.connect()
    
    # Store the meeting start time and an empty dict for user start times
    meeting_start = time.time()
    connections[ctx.guild.id] = {"vc": vc, "meeting_start": meeting_start, "user_start": {}}
    
    vc.start_recording(
        discord.sinks.WaveSink(),
        once_done,
        ctx.channel,
    )
    await ctx.respond("🔴 Listening to this conversation.")


async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    meeting_start = connections.get(channel.guild.id, {}).get("meeting_start", 0)
    user_start_times = connections.get(channel.guild.id, {}).get("user_start", {})

    await channel.send("🟡 Transcribing...")
    await sink.vc.disconnect()

    words_list = []

    for user_id, audio in sink.audio_data.items():
        payload = {"buffer": audio.file.read()}
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        
        words = response["results"]["channels"][0]["alternatives"][0]["words"]
        words = [word.to_dict() for word in words]

        if words:
            first_word_time = words[0]["start"]
            if user_id not in user_start_times:
                user_start_times[user_id] = first_word_time - meeting_start  # Aligning to meeting start
        
        user_offset = user_start_times[user_id]

        for word in words:
            words_list.append({
                "word": word["word"],
                "start": word["start"] + user_offset,
                "end": word["end"] + user_offset,
                "punctuated_word": word["punctuated_word"],
                "speaker": user_id,
            })

    words_list.sort(key=lambda x: x["start"])

    transcript = []
    current_speaker = None
    current_segment = {"speaker": None, "start": None, "end": None, "text": ""}
    
    for word in words_list:
        speaker = word["speaker"]
        if (speaker != current_speaker or 
            (current_segment["end"] is not None and word["start"] - current_segment["end"] > 2)):
            if current_speaker is not None:
                transcript.append(current_segment)
            current_speaker = speaker
            current_segment = {
                "speaker": speaker,
                "start": word["start"],
                "end": word["end"],
                "text": word["punctuated_word"]
            }
        else:
            current_segment["text"] += " " + word["punctuated_word"]
            current_segment["end"] = word["end"]

    if current_segment["speaker"] is not None:
        transcript.append(current_segment)

    with open("transcript.txt", "w") as f:
        for segment in transcript:
            start_minutes = int(segment["start"] // 60)
            start_seconds = int(segment["start"] % 60)
            # end_minutes = int(segment["end"] // 60)
            # end_seconds = int(segment["end"] % 60)
            f.write(f"[{start_minutes}:{start_seconds:02d}] {segment['speaker']}:\n{segment['text']}\n\n")

    await channel.send(file=discord.File("transcript.txt"))
    await channel.send("🟢 Transcription finished.")


@bot.command()
async def stop_recording(ctx):
    if ctx.guild.id in connections:
        await ctx.defer()
        vc_data = connections[ctx.guild.id]
        vc = vc_data["vc"]
        vc.stop_recording()
        del connections[ctx.guild.id]
        await ctx.delete()
    else:
        await ctx.respond("🚫 Not recording here")

bot.run("add-discord-bot-token")


# replace strip_header_ext in voice_client.py with this (search for the function name):
# @staticmethod
# def strip_header_ext(self, data):
#     import logging
#     logger = logging.getLogger(__name__)
#     try:
#         if data[0] == 0xBE and data[1] == 0xDE and len(data) > 4:
#             _, length = struct.unpack_from(">HH", data)
#             offset = 4 + length * 4
#             data = data[offset:]
#     except IndexError as e:
#         logger.warning(f"The IndexError occurred but we will ignore it! Just means this part of the data probably is 0 bytes.. Data: {data}")
#     return data