import gradio as gr
import os
from tqdm import tqdm
import random
import time
from moviepy.editor import *
from moviepy.audio.fx.audio_fadeout import audio_fadeout


class Img2Lookbook:

    def __init__(self, width, height, duration, fit, zoom_factor):

        self.output_width = width
        self.output_height = height
        self.duration = duration
        self.fit = fit
        self.zoom_factor = zoom_factor

        self.fps = 30

        self.add_watermark('', -1, -1)
        self.add_bg_color('#000000')
        self.add_fadeout(4.0)
        self.add_fit_image_duration_to_music(False)

    @staticmethod
    def is_image_file(file_path):
        _, file_extension = os.path.splitext(file_path)
        # Add other image file extensions as needed
        text_extensions = ['.jpg', '.png', '.jpeg', '.webp']
        return file_extension.lower() in text_extensions

    @staticmethod
    def is_sound_file(file_path):
        _, file_extension = os.path.splitext(file_path)
        # Add other image file extensions as needed
        text_extensions = ['.wav', '.mp3']
        return file_extension.lower() in text_extensions

    def add_fadeout(self, fadeout):
        self.fadeout = fadeout

    def add_bg_color(self, bg_color):
        self.bg_color = bg_color

    def add_watermark(self, watermark_filepath, watermark_x, watermark_y):

        self.watermark_filepath = watermark_filepath
        self.watermark_x = watermark_x
        self.watermark_y = watermark_y

    def add_fit_image_duration_to_music(self, fit):
        self.fit_image_duration_to_music = fit

    def hex_to_rgb(self, hex_string):
        hex_string = hex_string.lstrip('#')  # Remove the '#' if present
        rgb = tuple(int(hex_string[i:i+2], 16) for i in (0, 2, 4))
        return rgb

    def make(self, in_file):

        # bg
        bg_rgb = self.hex_to_rgb(self.bg_color)
        clip_bg = ColorClip(
            size=(self.output_width, self.output_height), color=[bg_rgb[0], bg_rgb[1], bg_rgb[2]])
        clip_bg = clip_bg.set_duration(self.duration).set_fps(self.fps)

        # image
        clip_fg = ImageClip(in_file)

        clip_fg = (clip_fg.fx(vfx.resize, height=self.output_height))
        if self.fit == "width":
            clip_fg = (clip_fg.fx(vfx.resize, width=self.output_width))

        clip_fg = clip_fg.set_duration(self.duration).set_fps(self.fps)
        clip_fg_init_size = clip_fg.size

        # scale up for zooming effect
        clip_effect = (clip_fg.fx(vfx.resize, 1.5))

        # white block
        clip_white = None
        try:
            clip_white = ColorClip(size=(
                (self.output_width-clip_fg.size[0])//2, self.output_height), color=[bg_rgb[0], bg_rgb[1], bg_rgb[2]])
            if self.fit == "width":
                clip_white = ColorClip(size=(
                    self.output_width, (self.output_height-clip_fg.size[1])//2), color=[bg_rgb[0], bg_rgb[1], bg_rgb[2]])

            clip_white = clip_white.set_duration(
                self.duration).set_fps(self.fps)

        except Exception as ex:
            print(str(ex))
            clip_white = None

        start_scale = 1
        end_scale = self.zoom_factor

        def scale_up_func(t):
            current_scale = start_scale + \
                (end_scale - start_scale) * (t / self.duration)
            return current_scale / 1.5

        # Apply the zoom-in effect using the resize method
        video_zoom_in = CompositeVideoClip([
            clip_bg,
            clip_effect.fx(vfx.resize, scale_up_func).set_position(
                lambda t: ('center', 'center'))
        ])

        if clip_white:
            video_zoom_in = CompositeVideoClip([
                clip_bg,
                clip_effect.fx(vfx.resize, scale_up_func).set_position(
                    lambda t: ('center', 'center')),
                clip_white.set_position((0, 0)),
                clip_white.set_position(
                    (clip_white.size[0]+clip_fg_init_size[0], 0))
            ])
            if self.fit == "width":
                video_zoom_in = CompositeVideoClip([
                    clip_bg,
                    clip_effect.fx(vfx.resize, scale_up_func).set_position(
                        lambda t: ('center', 'center')),
                    clip_white.set_position((0, 0)),
                    clip_white.set_position(
                        (0, clip_white.size[1]+clip_fg_init_size[1]))
                ])

        return video_zoom_in

    def batch_make_and_save(self, music_bg_directory_path, files, in_directory_path, random_images, out_directory_path):

        # Which music to use
        music_bg = None

        # Music background
        if music_bg_directory_path.strip() != '':
            music_bgs = [f for f in os.listdir(music_bg_directory_path) if os.path.isfile(
                os.path.join(music_bg_directory_path, f))]

            music_bgs = [f for f in music_bgs if self.is_sound_file(f)]

            if len(music_bgs) > 0:
                music_bg = random.sample(music_bgs, 1)[0]
                print(f'using bg music {music_bg}')

        # Get a list of all files in the directory
        if random_images:
            random.shuffle(files)
        else:
            files.sort()

        # Check if the directory already exists
        if not os.path.exists(out_directory_path):
            # If it does not exist, create it
            os.makedirs(out_directory_path)

        clip_videos = []

        # Loop through the operation and update the progress bar
        operation_length = len(files)
        if operation_length == 0:
            # Raise an Error with a custom error message
            raise gr.Error(
                "Error processing video: no images found in source images directory!")

        # Fit the image duration by music length
        if self.fit_image_duration_to_music:
            bg_music_clip = AudioFileClip(
                os.path.join(music_bg_directory_path, music_bg))

            self.duration = bg_music_clip.duration / len(files)

        with tqdm(total=operation_length) as pbar:

            # Add token to an input file at path in_file and save the result to out_file
            for i, file in enumerate(files):
                file_name, file_extension = os.path.splitext(file)

                in_file = os.path.join(in_directory_path, file)

                print(f'makeing video for image {file}')
                try:
                    if self.is_image_file(in_file):
                        clip_video = self.make(in_file)
                        clip_videos.append(clip_video)

                except Exception as ex:
                    print(str(ex))

                # Update the progress bar
                pbar.update(1)

        # Join videos

        # Videos
        videos_concat_clip = concatenate_videoclips(clip_videos)

        # Final
        final_video_clips = [videos_concat_clip]

        # Music background
        if music_bg is not None:

            bg_music_clip = AudioFileClip(
                os.path.join(music_bg_directory_path, music_bg))
            num_bg_music_repeat = int(
                videos_concat_clip.duration // bg_music_clip.duration) + 1
            cc_bg_music_clip = concatenate_audioclips(
                [bg_music_clip for _ in range(num_bg_music_repeat)]).set_duration(videos_concat_clip.duration)

            if self.fit_image_duration_to_music:
                cc_bg_music_clip = bg_music_clip

            # Fade out the audio
            fadeout_second = self.fadeout
            if fadeout_second > cc_bg_music_clip.duration:
                fadeout_second = cc_bg_music_clip.duration

            audio_fade = audio_fadeout(cc_bg_music_clip, fadeout_second)

            # Final
            videos_concat_clip = videos_concat_clip.set_audio(
                audio_fade)
            final_video_clips = [videos_concat_clip]

        # Watermark
        if self.watermark_filepath != '' and self.watermark_x > -1 and self.watermark_y > -1:
            watermark_clip = ImageClip(self.watermark_filepath)
            watermark_clip = watermark_clip.set_duration(
                videos_concat_clip.duration).set_fps(self.fps)
            watermark_clip = watermark_clip.set_position(
                (self.watermark_x, self.watermark_y))

            final_video_clips.append(watermark_clip)

        # Final
        final_video_clip = CompositeVideoClip(final_video_clips)
        if len(final_video_clips) == 1:
            final_video_clip = final_video_clips[0]

        unix_timestamp = int(time.time())
        final_output_video_filepath = os.path.join(
            out_directory_path, f'video-{unix_timestamp}.mp4')
        final_video_clip.write_videofile(
            final_output_video_filepath, fps=self.fps)

        return final_output_video_filepath

def separate_filenames_by_seed(filenames):
    seed_to_filenames = {}  # Create a dictionary to store sets of filenames by seed

    for filename in filenames:
        parts = filename.split('-')  # Split the filename by '-'
        if len(parts) == 2:
            num, seed_ext = parts
            seed, ext = seed_ext.split('.')  # Split the seed and extension

            # Check if the seed is already in the dictionary, if not, create a new set
            if seed not in seed_to_filenames:
                seed_to_filenames[seed] = set()

            # Add the filename to the set corresponding to its seed
            seed_to_filenames[seed].add(filename)

    return seed_to_filenames

def do_img2lookbook(
        img2lookbook_input_video_width,
        img2lookbook_input_video_height,
        img2lookbook_input_image_dir,
        img2lookbook_random_images,
        img2lookbook_input_bg_music_dir,
        img2lookbook_input_duration,
        img2lookbook_input_zoom_factor,
        img2lookbook_input_fit,
        img2lookbook_output_dir,
        img2lookbook_input_fadeout,
        img2lookbook_input_bg_color,
        img2lookbook_input_watermark_filepath,
        img2lookbook_input_watermark_x,
        img2lookbook_input_watermark_y,
        img2lookbook_fit_image_duration_to_music,
        img2lookbook_one_video_per_seed):

    image_2_img2lookbook = Img2Lookbook(img2lookbook_input_video_width, img2lookbook_input_video_height,
                                        img2lookbook_input_duration, img2lookbook_input_fit, img2lookbook_input_zoom_factor)
    image_2_img2lookbook.add_watermark(
        img2lookbook_input_watermark_filepath, img2lookbook_input_watermark_x, img2lookbook_input_watermark_y)

    image_2_img2lookbook.add_bg_color(img2lookbook_input_bg_color)

    image_2_img2lookbook.add_fadeout(img2lookbook_input_fadeout)

    image_2_img2lookbook.add_fit_image_duration_to_music(
        img2lookbook_fit_image_duration_to_music)

    try:
        videos = []

        # Get a list of all files in the directory
        files = [f for f in os.listdir(img2lookbook_input_image_dir) if os.path.isfile(
            os.path.join(img2lookbook_input_image_dir, f))]
        
        seed_to_filenames = {
            '0': files
        }
        if img2lookbook_one_video_per_seed:
            seed_to_filenames = separate_filenames_by_seed(files)

        # Print the sets of filenames by seed
        for seed, filenames in seed_to_filenames.items():
            vid = image_2_img2lookbook.batch_make_and_save(img2lookbook_input_bg_music_dir, list(filenames), img2lookbook_input_image_dir, img2lookbook_random_images, img2lookbook_output_dir)
            videos.append(vid)

        return videos[0]
    except Exception as ex:
        # Raise an Error with a custom error message
        raise gr.Error(f"Error processing video: {str(ex)}")


def update_duration_interactive(choice):
    return gr.update(interactive=not choice)


def make_ui():
    with gr.Blocks(analytics_enabled=False) as ui_component:
        gr.HTML(value="<p style='font-size: 1.4em; margin-bottom: 0.7em'>Watch 📺 <b><a href=\"https://www.youtube.com/@life-is-boring-so-programming\">video</a></b> for detailed explanation 🔍</p>")

        with gr.Row():
            with gr.Column():
                img2lookbook_input_image_dir = gr.Textbox(
                    label='Source images directory (*)', elem_id="img2lookbook_input_image_dir")

                img2lookbook_output_dir = gr.Textbox(
                    label='Destination directory (*)', elem_id="img2lookbook_output_dir")

                with gr.Row():
                    with gr.Column():
                        img2lookbook_input_video_width = gr.Slider(
                            label='Video width', value=1920, minimum=1, maximum=1920*4, step=1, elem_id="img2lookbook_input_video_width")
                    with gr.Column():
                        img2lookbook_input_video_height = gr.Slider(
                            label='Video height', value=1080, minimum=1, maximum=1080*4, step=1, elem_id="img2lookbook_input_video_height")

                img2lookbook_input_bg_music_dir = gr.Textbox(
                    label='Background music directory', elem_id="img2lookbook_input_bg_music_dir")

                img2lookbook_input_duration = gr.Slider(
                    label='Duration for each image animation (second)', value=4.0, minimum=0.1, maximum=10.0, step=0.1, elem_id="img2lookbook_input_duration")

                img2lookbook_input_zoom_factor = gr.Slider(
                    label='Zoom factor for each image animation', value=1.0, minimum=1.0, maximum=2.0, step=0.05, elem_id="img2lookbook_input_zoom_factor")

                img2lookbook_input_fit = gr.Radio(["height", "width"], value="height", label="Fit",
                                                  info="How the input images to be fitted into the video size", elem_id="img2lookbook_input_fit")

                with gr.Row():
                    img2lookbook_random = gr.Checkbox(
                        label='[Patreon bonus] Randomize input images', value=False, elem_id="img2lookbook_random")

                img2lookbook_one_video_per_seed = gr.Checkbox(
                    label='[Patreon bonus] Make one video per seed (for filename pattern [number]-[seed].png)', value=False, elem_id="img2lookbook_one_video_per_seed")

                img2lookbook_fit_image_duration_to_music = gr.Checkbox(
                    label='[Patreon bonus] Fit image duration to music length', value=False, elem_id="img2lookbook_fit_image_duration_to_music")

                img2lookbook_input_fadeout = gr.Slider(
                    label='[Patreon bonus] background music fadeout (second)', value=4.0, minimum=0.0, maximum=30.0, step=0.5, elem_id="img2lookbook_input_fadeout")

                img2lookbook_input_bg_color = gr.ColorPicker(
                    label='[Patreon bonus] background color', elem_id="img2lookbook_input_bg_color")

                img2lookbook_input_watermark_filepath = gr.Textbox(
                    label='[Patreon bonus] watermark filepath', elem_id="img2lookbook_input_watermark_filepath")

                with gr.Row():
                    with gr.Column():
                        img2lookbook_input_watermark_x = gr.Slider(
                            label='[Patreon bonus] watermark x position', value=10, minimum=0, maximum=1920*4, step=1, elem_id="img2lookbook_input_watermark_x")
                    with gr.Column():
                        img2lookbook_input_watermark_y = gr.Slider(
                            label='[Patreon bonus] watermark y position', value=10, minimum=0, maximum=1080*4, step=1, elem_id="img2lookbook_input_watermark_y")

                run_img2lookbook = gr.Button(
                    value="Run img2lookbook", variant='primary', elem_id="run_img2lookbook")

            with gr.Column():
                output_video = gr.Video(
                    label='Output video', elem_id="img2lookbook_output_video")

        # Disable img2lookbook_input_duration if enabled img2lookbook_fit_image_duration_to_music
        img2lookbook_fit_image_duration_to_music.change(fn=update_duration_interactive, inputs=img2lookbook_fit_image_duration_to_music, outputs=img2lookbook_input_duration)

        run_img2lookbook.click(fn=do_img2lookbook, inputs=[
            img2lookbook_input_video_width,
            img2lookbook_input_video_height,
            img2lookbook_input_image_dir,
            img2lookbook_random,
            img2lookbook_input_bg_music_dir,
            img2lookbook_input_duration,
            img2lookbook_input_zoom_factor,
            img2lookbook_input_fit,
            img2lookbook_output_dir,
            img2lookbook_input_fadeout,
            img2lookbook_input_bg_color,
            img2lookbook_input_watermark_filepath,
            img2lookbook_input_watermark_x,
            img2lookbook_input_watermark_y,
            img2lookbook_fit_image_duration_to_music,
            img2lookbook_one_video_per_seed
        ], outputs=output_video, api_name="do_img2lookbook")

        return ui_component
