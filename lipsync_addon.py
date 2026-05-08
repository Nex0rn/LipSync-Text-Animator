bl_info = {
    "name": "LipSync Text Animator",
    "author": "Nexcion",
    "version": (1, 0, 0),
    "blender": (4, 1, 0),
    "location": "View3D > Sidebar > LipSync",
    "description": "Converts text into mouth animations on a selected armature",
    "category": "Animation",
}

import bpy
import json
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import (
    StringProperty, IntProperty, FloatProperty,
    CollectionProperty, BoolProperty
)

VOWELS     = set("aeıiouAEIOU")
CONSONANTS = set("bcdfghjklmnprstvyzBCDFGHJKLMNPRSTVYZ")

def char_type(ch):
    if ch == " ":
        return "space"
    if ch in VOWELS:
        return "vowel"
    if ch in CONSONANTS:
        return "consonant"
    return None


class BoneTransform(PropertyGroup):
    bone_name : StringProperty()
    rot_mode  : StringProperty(default='QUATERNION')
    loc_x     : FloatProperty()
    loc_y     : FloatProperty()
    loc_z     : FloatProperty()
    rot_w     : FloatProperty(default=1.0)
    rot_x     : FloatProperty()
    rot_y     : FloatProperty()
    rot_z     : FloatProperty()
    euler_x   : FloatProperty()
    euler_y   : FloatProperty()
    euler_z   : FloatProperty()
    aa_w      : FloatProperty()
    aa_x      : FloatProperty()
    aa_y      : FloatProperty()
    aa_z      : FloatProperty(default=1.0)
    scale_x   : FloatProperty(default=1.0)
    scale_y   : FloatProperty(default=1.0)
    scale_z   : FloatProperty(default=1.0)


class CharPose(PropertyGroup):
    character  : StringProperty()
    bones      : CollectionProperty(type=BoneTransform)
    is_defined : BoolProperty(default=False)


class LipSyncSettings(PropertyGroup):
    input_text       : StringProperty(name="Text",             default="Hello")
    vowel_frames     : IntProperty(   name="Vowel (frames)",   default=4,   min=1, max=30)
    consonant_frames : IntProperty(   name="Consonant (frames)", default=2, min=1, max=30)
    space_frames     : IntProperty(   name="Space (frames)",   default=6,   min=1, max=60)
    speed_mult       : FloatProperty( name="Speed Multiplier", default=1.0, min=0.1, max=5.0, step=10)
    active_char      : StringProperty(name="Active Character", default="a", maxlen=1)
    poses            : CollectionProperty(type=CharPose)


def get_or_create_pose(settings, ch):
    for p in settings.poses:
        if p.character == ch:
            return p
    p = settings.poses.add()
    p.character = ch
    return p


def snapshot_armature(arm_obj):
    data = {}
    for pb in arm_obj.pose.bones:
        entry = {
            "rot_mode" : pb.rotation_mode,
            "loc"      : tuple(pb.location),
            "scale"    : tuple(pb.scale),
        }
        if pb.rotation_mode == 'QUATERNION':
            entry["rot"] = tuple(pb.rotation_quaternion)
        elif pb.rotation_mode == 'AXIS_ANGLE':
            entry["rot"] = tuple(pb.rotation_axis_angle)
        else:
            entry["rot"] = tuple(pb.rotation_euler)
        data[pb.name] = entry
    return data


def apply_snapshot_to_charpose(char_pose, snapshot):
    char_pose.bones.clear()
    for bname, entry in snapshot.items():
        bt           = char_pose.bones.add()
        bt.bone_name = bname
        bt.rot_mode  = entry["rot_mode"]
        bt.loc_x, bt.loc_y, bt.loc_z       = entry["loc"]
        bt.scale_x, bt.scale_y, bt.scale_z = entry["scale"]
        rot = entry["rot"]
        if entry["rot_mode"] == 'QUATERNION':
            bt.rot_w, bt.rot_x, bt.rot_y, bt.rot_z = rot
        elif entry["rot_mode"] == 'AXIS_ANGLE':
            bt.aa_w, bt.aa_x, bt.aa_y, bt.aa_z     = rot
        else:
            bt.euler_x, bt.euler_y, bt.euler_z      = rot
    char_pose.is_defined = True


def restore_pose_to_armature(arm_obj, char_pose):
    for bt in char_pose.bones:
        if bt.bone_name not in arm_obj.pose.bones:
            continue
        pb          = arm_obj.pose.bones[bt.bone_name]
        pb.location = (bt.loc_x, bt.loc_y, bt.loc_z)
        pb.scale    = (bt.scale_x, bt.scale_y, bt.scale_z)
        if pb.rotation_mode == 'QUATERNION':
            pb.rotation_quaternion = (bt.rot_w, bt.rot_x, bt.rot_y, bt.rot_z)
        elif pb.rotation_mode == 'AXIS_ANGLE':
            pb.rotation_axis_angle = (bt.aa_w, bt.aa_x, bt.aa_y, bt.aa_z)
        else:
            pb.rotation_euler = (bt.euler_x, bt.euler_y, bt.euler_z)


def _fcurve(action, data_path, index):
    for fc in action.fcurves:
        if fc.data_path == data_path and fc.array_index == index:
            return fc
    return action.fcurves.new(data_path=data_path, index=index)


def write_pose_to_action(action, arm_obj, frame):
    for pb in arm_obj.pose.bones:
        bname = pb.name

        base = f'pose.bones["{bname}"].location'
        for i, v in enumerate(pb.location):
            _fcurve(action, base, i).keyframe_points.insert(frame, v, options={'FAST'})

        if pb.rotation_mode == 'QUATERNION':
            base = f'pose.bones["{bname}"].rotation_quaternion'
            for i, v in enumerate(pb.rotation_quaternion):
                _fcurve(action, base, i).keyframe_points.insert(frame, v, options={'FAST'})
        elif pb.rotation_mode == 'AXIS_ANGLE':
            base = f'pose.bones["{bname}"].rotation_axis_angle'
            for i, v in enumerate(pb.rotation_axis_angle):
                _fcurve(action, base, i).keyframe_points.insert(frame, v, options={'FAST'})
        else:
            base = f'pose.bones["{bname}"].rotation_euler'
            for i, v in enumerate(pb.rotation_euler):
                _fcurve(action, base, i).keyframe_points.insert(frame, v, options={'FAST'})

        base = f'pose.bones["{bname}"].scale'
        for i, v in enumerate(pb.scale):
            _fcurve(action, base, i).keyframe_points.insert(frame, v, options={'FAST'})


class LIPSYNC_OT_SavePose(Operator):
    bl_idname      = "lipsync.save_pose"
    bl_label       = "Save Pose"
    bl_description = "Save the current pose of the selected armature for the active character"

    def execute(self, context):
        settings = context.scene.lipsync_settings
        arm_obj  = context.active_object

        if not arm_obj or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Please select an Armature first.")
            return {'CANCELLED'}

        ch = settings.active_char
        if ch == '_':
            ch = ' '
        if not ch or len(ch) != 1:
            self.report({'ERROR'}, "Enter a single valid character (use '_' for space).")
            return {'CANCELLED'}

        snapshot  = snapshot_armature(arm_obj)
        char_pose = get_or_create_pose(settings, ch)
        apply_snapshot_to_charpose(char_pose, snapshot)

        display = '_' if ch == ' ' else ch
        self.report({'INFO'}, f"Pose saved for '{display}' ({len(snapshot)} bones).")
        return {'FINISHED'}


class LIPSYNC_OT_ClearPose(Operator):
    bl_idname      = "lipsync.clear_pose"
    bl_label       = "Delete Pose"
    bl_description = "Delete the saved pose for the active character"

    def execute(self, context):
        settings = context.scene.lipsync_settings
        ch = settings.active_char
        if ch == '_':
            ch = ' '
        for i, p in enumerate(settings.poses):
            if p.character == ch:
                settings.poses.remove(i)
                self.report({'INFO'}, f"Pose for '{ch if ch != ' ' else '_'}' deleted.")
                return {'FINISHED'}
        self.report({'WARNING'}, "No saved pose found for this character.")
        return {'FINISHED'}


class LIPSYNC_OT_PreviewPose(Operator):
    bl_idname      = "lipsync.preview_pose"
    bl_label       = "Preview Pose"
    bl_description = "Apply the saved pose for the active character in the viewport"

    def execute(self, context):
        settings = context.scene.lipsync_settings
        arm_obj  = context.active_object

        if not arm_obj or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Please select an Armature first.")
            return {'CANCELLED'}

        ch = settings.active_char
        if ch == '_':
            ch = ' '

        for p in settings.poses:
            if p.character == ch and p.is_defined:
                restore_pose_to_armature(arm_obj, p)
                return {'FINISHED'}

        self.report({'WARNING'}, f"No saved pose for '{ch if ch != ' ' else '_'}'.")
        return {'CANCELLED'}


class LIPSYNC_OT_Animate(Operator):
    bl_idname      = "lipsync.animate"
    bl_label       = "Generate Animation"
    bl_description = "Convert the input text into keyframes starting from the current frame"
    bl_options     = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.lipsync_settings
        arm_obj  = context.active_object

        if not arm_obj or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Please select an Armature first.")
            return {'CANCELLED'}

        text = settings.input_text
        if not text:
            self.report({'ERROR'}, "Text cannot be empty.")
            return {'CANCELLED'}

        if not arm_obj.animation_data:
            arm_obj.animation_data_create()
        if not arm_obj.animation_data.action:
            arm_obj.animation_data.action = bpy.data.actions.new("LipSync_Action")
        action = arm_obj.animation_data.action

        mult      = settings.speed_mult
        v_frames  = max(1, round(settings.vowel_frames     * mult))
        c_frames  = max(1, round(settings.consonant_frames * mult))
        sp_frames = max(1, round(settings.space_frames     * mult))

        start_frame   = context.scene.frame_current
        current_frame = start_frame
        missing_chars = set()
        animated      = 0

        prev_mode = arm_obj.mode
        if context.active_object != arm_obj:
            context.view_layer.objects.active = arm_obj
        if prev_mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        for ch in text:
            ctype = char_type(ch)
            if ctype is None:
                continue

            char_pose = None
            for p in settings.poses:
                if p.character == ch and p.is_defined:
                    char_pose = p
                    break

            if char_pose is None:
                missing_chars.add('_' if ch == ' ' else ch)
            else:
                restore_pose_to_armature(arm_obj, char_pose)
                write_pose_to_action(action, arm_obj, current_frame)
                animated += 1

            if ctype == "vowel":
                current_frame += v_frames
            elif ctype == "consonant":
                current_frame += c_frames
            else:
                current_frame += sp_frames

        for fc in action.fcurves:
            fc.update()

        if prev_mode != 'POSE':
            bpy.ops.object.mode_set(mode=prev_mode)

        context.scene.frame_end = max(context.scene.frame_end, current_frame)

        msg = f"{animated} characters written  |  frames {start_frame} → {current_frame - 1}"
        if missing_chars:
            msg += f"  |  Missing poses: {', '.join(sorted(missing_chars))}"
            self.report({'WARNING'}, msg)
        else:
            self.report({'INFO'}, msg)

        return {'FINISHED'}


class LIPSYNC_OT_ExportPoses(Operator):
    bl_idname   = "lipsync.export_poses"
    bl_label    = "Export Poses (JSON)"
    filepath    : StringProperty(subtype='FILE_PATH', default="lipsync_poses.json")
    filter_glob : StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        settings = context.scene.lipsync_settings
        data = {}
        for p in settings.poses:
            if not p.is_defined:
                continue
            bones = {}
            for bt in p.bones:
                bones[bt.bone_name] = {
                    "rot_mode" : bt.rot_mode,
                    "loc"      : [bt.loc_x,   bt.loc_y,   bt.loc_z],
                    "rot_q"    : [bt.rot_w,   bt.rot_x,   bt.rot_y,   bt.rot_z],
                    "rot_e"    : [bt.euler_x, bt.euler_y, bt.euler_z],
                    "rot_aa"   : [bt.aa_w,    bt.aa_x,    bt.aa_y,    bt.aa_z],
                    "scale"    : [bt.scale_x, bt.scale_y, bt.scale_z],
                }
            data[p.character] = bones

        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.report({'INFO'}, f"Exported: {self.filepath}")
        return {'FINISHED'}


class LIPSYNC_OT_ImportPoses(Operator):
    bl_idname   = "lipsync.import_poses"
    bl_label    = "Import Poses (JSON)"
    filepath    : StringProperty(subtype='FILE_PATH')
    filter_glob : StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        settings = context.scene.lipsync_settings
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.report({'ERROR'}, f"Could not read file: {e}")
            return {'CANCELLED'}

        count = 0
        for ch, bones in data.items():
            cp = get_or_create_pose(settings, ch)
            cp.bones.clear()
            for bname, td in bones.items():
                bt            = cp.bones.add()
                bt.bone_name  = bname
                bt.rot_mode   = td.get("rot_mode", "QUATERNION")
                bt.loc_x,   bt.loc_y,   bt.loc_z    = td["loc"]
                bt.rot_w,   bt.rot_x,   bt.rot_y,   bt.rot_z = td["rot_q"]
                bt.euler_x, bt.euler_y, bt.euler_z  = td["rot_e"]
                bt.aa_w,    bt.aa_x,    bt.aa_y,    bt.aa_z  = td["rot_aa"]
                bt.scale_x, bt.scale_y, bt.scale_z  = td["scale"]
            cp.is_defined = True
            count += 1

        self.report({'INFO'}, f"{count} character poses imported.")
        return {'FINISHED'}


class LIPSYNC_PT_MainPanel(Panel):
    bl_label       = "LipSync Text Animator"
    bl_idname      = "LIPSYNC_PT_main"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "LipSync"

    def draw(self, context):
        layout   = self.layout
        settings = context.scene.lipsync_settings
        arm_obj  = context.active_object
        is_arm   = arm_obj and arm_obj.type == 'ARMATURE'

        box = layout.box()
        if is_arm:
            box.label(text=f"Armature: {arm_obj.name}", icon='ARMATURE_DATA')
        else:
            box.label(text="Select an Armature", icon='ERROR')

        box = layout.box()
        box.label(text="Character → Pose Mapping", icon='POSE_HLT')

        row = box.row(align=True)
        row.prop(settings, "active_char", text="Char")
        row.operator("lipsync.preview_pose", text="", icon='HIDE_OFF')

        ch_key  = ' ' if settings.active_char == '_' else settings.active_char
        defined = any(p.character == ch_key and p.is_defined for p in settings.poses)
        box.label(
            text="Pose saved ✓" if defined else "No pose saved yet",
            icon='CHECKMARK' if defined else 'RADIOBUT_OFF'
        )

        row = box.row(align=True)
        row.operator("lipsync.save_pose",  text="Save Current Pose", icon='REC')
        row.operator("lipsync.clear_pose", text="",                  icon='TRASH')

        box.separator()
        defined_chars = [p.character for p in settings.poses if p.is_defined]
        if defined_chars:
            box.label(text=f"Defined: {len(defined_chars)} characters")
            grid = box.grid_flow(row_major=True, columns=10, even_columns=True)
            for ch in sorted(defined_chars):
                grid.label(text='_' if ch == ' ' else ch)
        else:
            box.label(text="(no poses defined yet)", icon='INFO')

        box = layout.box()
        box.label(text="Frame Durations", icon='TIME')
        col = box.column(align=True)
        col.prop(settings, "vowel_frames")
        col.prop(settings, "consonant_frames")
        col.prop(settings, "space_frames")
        box.prop(settings, "speed_mult", slider=True)

        box = layout.box()
        box.label(text="Text & Animation", icon='FONT_DATA')
        box.prop(settings, "input_text", text="")

        text      = settings.input_text
        ch_count  = sum(1 for c in text if char_type(c) is not None)
        undefined = sum(1 for c in text if char_type(c) is None)
        row = box.row()
        row.label(text=f"{ch_count} characters", icon='INFO')
        if undefined:
            row.label(text=f"({undefined} skipped)", icon='ERROR')

        row = box.row()
        row.scale_y = 1.6
        row.enabled = is_arm
        row.operator("lipsync.animate", icon='PLAY')

        box = layout.box()
        box.label(text="Pose Library", icon='FILE_FOLDER')
        row = box.row(align=True)
        row.operator("lipsync.export_poses", text="Export", icon='EXPORT')
        row.operator("lipsync.import_poses", text="Import", icon='IMPORT')


classes = (
    BoneTransform,
    CharPose,
    LipSyncSettings,
    LIPSYNC_OT_SavePose,
    LIPSYNC_OT_ClearPose,
    LIPSYNC_OT_PreviewPose,
    LIPSYNC_OT_Animate,
    LIPSYNC_OT_ExportPoses,
    LIPSYNC_OT_ImportPoses,
    LIPSYNC_PT_MainPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lipsync_settings = bpy.props.PointerProperty(type=LipSyncSettings)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.lipsync_settings


if __name__ == "__main__":
    register()
