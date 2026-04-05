from manim import *
import json
import os
import shutil
import glob
import numpy as np
from gtts import gTTS
from mutagen.mp3 import MP3

# ==========================================
# 0. HELPER: TTS SERVICE
# ==========================================
class TTSService:
    def generate_audio(self, text, step_index):
        if not text or not text.strip():
            return None, 0
        filename = f"voiceover_{step_index}.mp3"
        try:
            tts = gTTS(text=text, lang='en')
            tts.save(filename)
            audio = MP3(filename)
            return filename, audio.info.length
        except Exception:
            return filename, 2.0 

# ==========================================
# 1. LEGO BLOCK: DynamicStack (TURBO SPEED)
# ==========================================
class DynamicStack:
    def __init__(self, frame_name="Global Frame", capacity=3):
        self.frame_name = frame_name
        self.capacity = max(capacity, 1)
        self.var_height = 1.0
        self.var_spacing = 0.2
        self.header_height = 0.8
        self.padding = 0.5
        
        self.content_height = (self.capacity * self.var_height) + ((self.capacity - 1) * self.var_spacing)
        self.total_height = self.content_height + self.header_height + (self.padding * 2)
        
        self.width = 4.5
        self.center_point = RIGHT * 3.5 

    def generate_mobjects(self):
        self.rect = Rectangle(height=self.total_height, width=self.width, color=WHITE)
        self.rect.move_to(self.center_point)
        self.header_bg = Rectangle(height=self.header_height, width=self.width, color=WHITE)
        self.header_bg.set_fill(GRAY, opacity=0.5)
        header_pos = self.rect.get_top() + (DOWN * (self.header_height / 2))
        self.header_bg.move_to(header_pos)
        self.label = Text(self.frame_name, font_size=24, color=WHITE)
        self.label.move_to(self.header_bg.get_center())
        return VGroup(self.rect, self.header_bg, self.label)

    def get_animations(self):
        # FAST: Create everything in 0.5s total
        return AnimationGroup(
            Create(self.rect), 
            FadeIn(self.header_bg), 
            Write(self.label),
            run_time=0.5,
            lag_ratio=0.1
        )
    
    def get_slot_position(self, index):
        base_y = self.rect.get_bottom()[1] + self.padding + (self.var_height / 2)
        offset_y = index * (self.var_height + self.var_spacing)
        target_y = base_y + offset_y
        target_x = self.rect.get_center()[0]
        return np.array([target_x, target_y, 0])

# ==========================================
# 2. LEGO BLOCK: VarCreate (SPLIT ANIMATION)
# ==========================================
class VarCreate:
    def __init__(self, name, value, target_position):
        self.name = name
        self.value = str(value)
        self.target_pos = target_position

    def generate_mobjects(self):
        self.box = Rectangle(height=1.0, width=3.8, color=BLUE)
        self.box.set_fill(BLUE, opacity=0.2)
        self.box.move_to(self.target_pos)
        self.label = Text(self.name, font_size=24, color=YELLOW)
        if self.label.width > 1.6: self.label.scale_to_fit_width(1.6)
        self.label.next_to(self.box.get_left(), RIGHT, buff=0.2)
        self.value_text = Text(self.value, font_size=24, color=WHITE)
        if self.value_text.width > 1.6: self.value_text.scale_to_fit_width(1.6)
        self.value_text.next_to(self.box.get_right(), LEFT, buff=0.2)
        return VGroup(self.box, self.label, self.value_text)

    # We split the animations into two stages for better sync control
    def get_setup_animations(self):
        """Stage 1: Box and Name"""
        return [
            FadeIn(self.box, run_time=0.3), 
            Write(self.label, run_time=0.4)
        ]

    def get_value_animation(self):
        """Stage 2: Value Pop"""
        return Write(self.value_text, run_time=0.4)

# ==========================================
# 3. CODIMA V3 (Unchanged)
# ==========================================
class Codima(VGroup):
    def __init__(self):
        super().__init__()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_path = os.path.join(current_dir, "assets", "mascotStates")
        
        self.states = {
            "idle":     os.path.join(self.assets_path, "idle.svg"),
            "thinking": os.path.join(self.assets_path, "thinking.svg"),
            "pointing": os.path.join(self.assets_path, "pointing.svg")
        }
        self.current_state = "idle"
        
        # Body
        self.body = self.load_state_safe("idle")
        self.body.height = 2.5
        self.body.to_corner(DL, buff=0.5)
        
        # Mouth (Inside Visor)
        face_center = self.body.get_top() + (DOWN * 1.35) 
        self.mouth = Ellipse(width=0.2, height=0.02, color=WHITE)
        self.mouth.set_fill(WHITE, opacity=1)
        self.mouth.move_to(face_center)
        self.mouth.set_z_index(10)
        self.mouth.set_opacity(0)
        
        self.add(self.body, self.mouth)

    def load_state_safe(self, state_name):
        path = self.states.get(state_name, "")
        try:
            if not os.path.exists(path): raise FileNotFoundError
            svg = SVGMobject(path)
            if len(svg) == 0: raise ValueError("Empty SVG")
            return svg
        except Exception as e:
            return Circle(radius=1, color=RED, fill_opacity=1)

    def animate_to_state(self, new_state_name):
        if new_state_name == self.current_state: return None
        if new_state_name not in self.states: return None
        new_body = self.load_state_safe(new_state_name)
        new_body.match_height(self.body)
        new_body.move_to(self.body.get_center())
        new_body.align_to(self.body, DOWN)
        self.current_state = new_state_name
        return Transform(self.body, new_body)

    def get_pace_anim(self, duration=1.0):
        n_steps = max(1, int(duration / 0.8))
        step_time = duration / n_steps
        anims = []
        for _ in range(n_steps):
            anims.append(AnimationGroup(ApplyMethod(self.shift, RIGHT * 0.2, run_time=step_time*0.25, rate_func=linear), ApplyMethod(self.shift, UP * 0.1, run_time=step_time*0.25, rate_func=there_and_back)))
            anims.append(AnimationGroup(ApplyMethod(self.shift, LEFT * 0.4, run_time=step_time*0.5, rate_func=linear), ApplyMethod(self.shift, UP * 0.1, run_time=step_time*0.5, rate_func=there_and_back)))
            anims.append(AnimationGroup(ApplyMethod(self.shift, RIGHT * 0.2, run_time=step_time*0.25, rate_func=linear), ApplyMethod(self.shift, UP * 0.1, run_time=step_time*0.25, rate_func=there_and_back)))
        return Succession(*anims)

    def get_talk_anim(self, duration=1.0):
        self.mouth.set_opacity(1)
        n_flaps = max(1, int(duration / 0.15))
        flap_time = duration / n_flaps
        flaps = []
        for _ in range(n_flaps):
            flaps.append(ApplyMethod(self.mouth.stretch_to_fit_height, 0.12, run_time=flap_time/2, rate_func=there_and_back))
        return Succession(*flaps)

# ==========================================
# 4. THE SCENE (SYNC & SPEED FIX)
# ==========================================
class CodeAnimatorEngine(Scene):
    def __init__(self, script_data, **kwargs):
        self.script_data = script_data
        self.tts = TTSService()
        super().__init__(**kwargs)

    def construct(self):
        if isinstance(self.script_data, str): data = json.loads(self.script_data)
        else: data = self.script_data
        script_sequence = data.get("sequence", [])

        code_header = Text("Instruction:", font_size=24, color=GRAY).to_edge(UP).to_edge(LEFT)
        current_code_line = Text("...", font="Monospace", font_size=28).next_to(code_header, DOWN).align_to(code_header, LEFT)
        
        self.codima = Codima()
        subtitle = Text("", font_size=24, color=WHITE).next_to(self.codima, RIGHT, buff=0.5).to_edge(DOWN, buff=1.0)
        self.add(code_header, current_code_line, subtitle, self.codima)
        
        self.variables_on_screen = [] 
        self.active_stack = None       
        total_vars = sum(1 for step in script_sequence if step.get("type") == "VarCreate")

        for i, step in enumerate(script_sequence):
            code_text = step.get("code", "")
            narration = step.get("narration", "")
            action = step.get("type", "")
            params = step.get("params", {})
            mascot_state = step.get("mascot", "idle")

            audio_path, audio_dur = self.tts.generate_audio(narration, i)
            if audio_path: self.add_sound(audio_path)
            
            # Use audio duration, but clamp it to at least 1.5s so animation isn't instant
            step_duration = max(1.5, audio_dur)

            # --- PREPARE UI UPDATES ---
            new_code = Text(code_text, font="Monospace", font_size=28, color=GREEN).next_to(code_header, DOWN).align_to(code_header, LEFT)
            new_sub = Text(narration, font_size=24, color=WHITE)
            if new_sub.width > 7: new_sub.scale_to_fit_width(7.5)
            new_sub.to_edge(DOWN, buff=0.8).to_edge(RIGHT, buff=0.5)
            if new_sub.get_left()[0] < -3: new_sub.shift(RIGHT * ( -3 - new_sub.get_left()[0]))

            # --- PHASE 1: MASCOT TRANSITION (Quick) ---
            state_anim = self.codima.animate_to_state(mascot_state)
            if state_anim:
                self.play(state_anim, run_time=0.4) # Fast morph
            
            # --- PHASE 2: EXECUTION ---
            
            # A. Common UI animations
            ui_anims = [ReplacementTransform(current_code_line, new_code), Transform(subtitle, new_sub)]
            current_code_line = new_code
            
            stack_anim = None
            var_setup_anims = []
            var_value_anim = None
            
            # B. Build Logic Animations
            if action == "VarCreate":
                # Stack Check
                t_scope = params.get("scope", "Global")
                if not self.active_stack or self.active_stack.frame_name != t_scope:
                    self.active_stack = DynamicStack(t_scope, capacity=total_vars)
                    self.active_stack.generate_mobjects()
                    # Stack animates FAST now (defined in DynamicStack class)
                    stack_anim = self.active_stack.get_animations()

                # Variable Logic
                idx = len(self.variables_on_screen)
                pos = self.active_stack.get_slot_position(idx)
                var_b = VarCreate(params["name"], params["value"], pos)
                m_obj = var_b.generate_mobjects()
                self.variables_on_screen.append(m_obj)
                
                # Split animations:
                var_setup_anims = var_b.get_setup_animations() # Box + Name
                var_value_anim = var_b.get_value_animation()   # Value

            # --- PHASE 3: PLAYING WITH SYNC ---
            # We split the available audio time into two halves to sync visually
            
            half_time = step_duration / 2.0
            
            # LOOP 1: Setup (Box + Name)
            # Talking/Pacing loops must span both halves
            loop1_talk = []
            if narration.strip(): loop1_talk.append(self.codima.get_talk_anim(duration=half_time))
            if mascot_state == "thinking": loop1_talk.append(self.codima.get_pace_anim(duration=half_time))

            group1 = ui_anims
            if stack_anim: group1.append(stack_anim)
            if var_setup_anims: group1.extend(var_setup_anims)
            
            self.play(*group1, *loop1_talk, run_time=half_time)
            
            # LOOP 2: Value (The "Result")
            # This runs during the second half of the audio
            loop2_talk = []
            if narration.strip(): loop2_talk.append(self.codima.get_talk_anim(duration=half_time))
            if mascot_state == "thinking": loop2_talk.append(self.codima.get_pace_anim(duration=half_time))
            
            group2 = []
            if var_value_anim: group2.append(var_value_anim)
            
            # If no value animation (e.g. just narration), we just wait/talk
            if group2:
                self.play(*group2, *loop2_talk, run_time=half_time)
            else:
                self.play(*loop2_talk, run_time=half_time)

            self.codima.mouth.set_opacity(0)

def render_code_animation(json_input):
    output_folder = "./output_video"
    config.media_dir = output_folder
    config.verbosity = "WARNING"
    config.quality = "low_quality"
    config.preview = False 
    scene = CodeAnimatorEngine(script_data=json_input)
    scene.render()
    
    final_filename = "CodeAnimatorEngine.mp4"
    found_video = None
    for root, dirs, files in os.walk(output_folder):
        if final_filename in files:
            found_video = os.path.join(root, final_filename)
            break
    target_video = "final_output.mp4"
    final_path = os.path.abspath(target_video)
    if found_video:
        if os.path.exists(target_video): os.remove(target_video)
        shutil.move(found_video, target_video)
    else: return None
    if os.path.exists(output_folder): shutil.rmtree(output_folder)
    for f in glob.glob("voiceover_*.mp3"): 
        try: os.remove(f)
        except: pass
    return final_path