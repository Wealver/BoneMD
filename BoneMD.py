bl_info = {
    "name": "BoneMD",
    "author": "Wealver",
    "version": (0, 2),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Bone Tools",
    "description": "Renaming original PD rigging scheme and quick reparenting them to something more comprehensable, including a bone axis roller. Made easily editable depending on the need!",
    "category": "Rigging",
}

import bpy
import re
import math
from mathutils import Vector

# ---------------------------
# Renaming Bones (original -> new name)
# ---------------------------

RENAMING_RULES = {
    "kl_kosi_etc_wj": "Hips",
    "n_hara_b_wj_ex": "Spine",
    "n_hara_c_wj_ex": "Chest",
    "kl_mune_b": "UpperChest",
    "j_kao": "Head",
    "n_kubi": "Neck",
    "n_waki_*": "Shoulder*",
    "kl_waki_*": "Shoulder*",
    "n_skata_*": "UpperArm*",
    "j_ude_*": "LowerArm*",
    "n_momo_*": "UpperLeg_Extra*",
    "j_momo_*": "UpperLeg*",
    "j_sune_*": "LowerLeg*",
    "n_asi_*": "Foot*",
    "kl_asi_*": "Foot*",
    "n_toe_*": "Toe*",
    "kl_toe_*": "Toe*",
    "n_hiji_*": "Elbow*",
    "n_hiza_*": "Knee*",
    "n_sude_*": "LowerArm*",
    "n_ste_*": "Wrist",
    "kl_te_*": "Hand",
    "nl_oya_*": "Thumb",
    "nl_hito_*": "Index",
    "nl_naka_*": "Middle",
    "nl_kusu_*": "Ring",
    "nl_ko_*": "Pinky",
    "n_eye_*": "Eye",
    "kl_ago_": "Jaw",
    "tl_mabu_*_d": "Lower_Eyelid*",
    "tl_mabu_*_u": "Upper_Eyelid*",
    "tl_mayu*": "Brow*",
    "tl_kuti_u_*": "Mouth_Upper*",
    "tl_kuti_d_*": "Mouth_Lower*",
    "tl_kuti_ds_*": "Lip_Corner*",
    "tl_eyelid_*": "Eyefold*",
    "tl_tooth_upper": "Upper_Teeth"
}

REPARENT_RULES = {
    "Head": "Neck",
    "Neck": "UpperChest",
    "UpperChest": "Chest",
    "Chest": "Spine",
    "Spine": "Hips",
    "Shoulder*": "UpperChest",
    "UpperArm*": "Shoulder*",
    "LowerArm*": "UpperArm*",
    "Wrist*": "LowerArm*",
    "Hand*": "Wrist*",
    "UpperLeg*": "Hips",
    "Knee*": "UpperLeg*",
    "LowerLeg*": "UpperLeg*",
    "Knee*": "LowerLeg*",
    "Foot*": "LowerLeg*",
    "Toe*": "Foot*",
    "UpperLeg_Extra*": "UpperLeg*",
}


# ---------------------------
# Code portions, would not reccomend messing with. 
# ---------------------------


def translate_bone_name(old_name: str) -> str:
    name = old_name.lower()
    for jp, en in RENAMING_RULES.items():
        if "*" in jp:
            base = jp.replace("_*", "")
            if base in name:
                new_name = en.replace("*", "")
                if "_l" in name:
                    return new_name + ".L"
                elif "_r" in name:
                    return new_name + ".R"
                else:
                    return new_name
        else:
            if jp in name:
                return en
    return old_name

def reparent_bones(arm):
    if arm is None or arm.type != "ARMATURE":
        return

    bpy.ops.object.mode_set(mode='EDIT')
    ebones = arm.data.edit_bones
    lower_to_actual = {b.name.lower(): b.name for b in ebones}

    def is_numbered(bname):
        return bool(re.search(r'\.\d+$', bname))

    def strip_number(bname):
        return re.sub(r'\.\d+$', '', bname)

    sorted_rules = sorted(REPARENT_RULES.items(), key=lambda kv: -len(kv[0]))

    for child_pattern, parent_pattern in sorted_rules:
        child_base_pattern = child_pattern.replace('*', '').lower()
        for eb in list(ebones):
            name = eb.name
            if is_numbered(name):
                continue

            lname = name.lower()
            matched = False
            if '*' in child_pattern:
                if child_base_pattern in lname:
                    matched = True
            else:
                if lname == child_pattern.lower():
                    matched = True

            if not matched:
                continue

            parent_base = parent_pattern.replace('*', '')
            side = ''
            if name.endswith('.L') or name.endswith('.R'):
                side = name[-2:]

            p_candidate = parent_base + side
            parent_actual = p_candidate if p_candidate in ebones else lower_to_actual.get(p_candidate.lower())
            if not parent_actual:
                parent_actual = parent_base if parent_base in ebones else lower_to_actual.get(parent_base.lower())
            if not parent_actual:
                continue

            if parent_actual == name:
                continue

            head_world = arm.matrix_world @ eb.head
            tail_world = arm.matrix_world @ eb.tail

            eb.parent = ebones[parent_actual]
            eb.use_connect = False

            eb.head = arm.matrix_world.inverted() @ head_world
            eb.tail = arm.matrix_world.inverted() @ tail_world

    bpy.ops.object.mode_set(mode='OBJECT')

# ---------------------------
# Operators
# ---------------------------

class BONE_OT_align_roll(bpy.types.Operator):
    """Align selected bone roll to target object"""
    bl_idname = "bone.align_roll"
    bl_label = "Align Bone Roll To Target"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        name="Direction",
        items=[
            ('TOWARD', "Toward Target", ""),
            ('AWAY', "Away From Target", ""),
        ],
        default='TOWARD'
    )

    axis: bpy.props.EnumProperty(
        name="Axis",
        items=[
            ('X', "Align X Axis", ""),
            ('Z', "Align Z Axis", ""),
        ],
        default='X'
    )

    def execute(self, context):
        arm = context.object

        if not arm or arm.type != "ARMATURE":
            self.report({"ERROR"}, "Select an Armature.")
            return {'CANCELLED'}

        if arm.mode != 'EDIT':
            self.report({"ERROR"}, "Must be in Edit Mode.")
            return {'CANCELLED'}

        target = context.scene.bonemd_roll_target
        if not target:
            self.report({"ERROR"}, "Set a Target Object first.")
            return {'CANCELLED'}

        target_world = target.matrix_world.translation

        for bone in arm.data.edit_bones:
            if not bone.select:
                continue

            head_world = arm.matrix_world @ bone.head
            tail_world = arm.matrix_world @ bone.tail

            y_axis = (tail_world - head_world).normalized()
            to_target = target_world - head_world

            if self.direction == 'AWAY':
                to_target.negate()

            if to_target.length < 1e-6:
                continue

            to_target.normalize()
            projected = to_target - y_axis * to_target.dot(y_axis)

            if projected.length < 1e-6:
                continue

            projected.normalize()

            bone_matrix_world = arm.matrix_world @ bone.matrix.to_4x4()
            bone_basis = bone_matrix_world.to_3x3()

            if self.axis == 'X':
                current_axis = bone_basis @ Vector((1, 0, 0))
            else:
                current_axis = bone_basis @ Vector((0, 0, 1))

            current_axis.normalize()

            angle = current_axis.angle(projected)
            cross = current_axis.cross(projected)

            if cross.dot(y_axis) < 0:
                angle = -angle

            bone.roll += angle

        self.report({"INFO"}, "Bone roll aligned.")
        return {'FINISHED'}


class BONE_OT_rename(bpy.types.Operator):
    bl_idname = "bone.rename"
    bl_label = "Rename Bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm = context.object
        if not arm or arm.type != "ARMATURE":
            self.report({"ERROR"}, "Select an Armature.")
            return {'CANCELLED'}

        count = 0
        for bone in arm.data.bones:
            old = bone.name
            new = translate_bone_name(old)
            if old != new:
                bone.name = new
                count += 1

        self.report({"INFO"}, f"Renamed {count} bones.")
        return {'FINISHED'}

class BONE_OT_reparent(bpy.types.Operator):
    bl_idname = "bone.reparent"
    bl_label = "Reparent Bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm = context.object
        if not arm or arm.type != "ARMATURE":
            self.report({"ERROR"}, "Select an Armature.")
            return {'CANCELLED'}
        reparent_bones(arm)
        self.report({"INFO"}, "Bones reparented.")
        return {'FINISHED'}


class BONE_PT_panel(bpy.types.Panel):
    bl_label = "BoneMD"
    bl_idname = "BONE_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BoneMD"

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="BoneMD Tool", icon="INFO")
        box.label(text="Rename bones into Unity-ready names.")
        box.label(text="Select the armature before using rename and then reparent.")
        box.label(text="Not all bones will be perfectly reparent or renamed, check manually what you need to adjust.")

        layout.operator("bone.rename")
        layout.operator("bone.reparent")

        layout.separator()
        layout.label(text="Roll Tools", icon="CON_ROTLIKE")
        layout.prop(context.scene, "bonemd_roll_target")
        layout.label(text="1. Make or choose an object to align the roll to. (Make an empty and place it in the center for example.)")
        layout.label(text="2. Select bones you'd want to rotate.)")
        layout.label(text="3. Press the button and use small menu on the bottom left to chose between options.)")
        layout.operator("bone.align_roll")

        credit = layout.box()
        credit.label(text="Made by Wealver", icon="USER")
        credit.label(text="If there's any issues, contact me on discord!", icon="INFO")

# Registration
classes = (
    BONE_OT_rename,
    BONE_OT_reparent,
    BONE_OT_align_roll,
    BONE_PT_panel
)

def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.bonemd_roll_target = bpy.props.PointerProperty(
        name="Roll Target",
        type=bpy.types.Object
    )

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.bonemd_roll_target

if __name__ == "__main__":
    register()
