bl_info = {
    "name": "BoneMD (From fbx rips all the way to unity)",
    "author": "Wealver",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Bone Tools",
    "description": "Renaming original PD rigging scheme and quick reparenting them to something more comprehensable. Made easily editable depending on the need!",
    "category": "Rigging",
}

import bpy

# ---------------------------
# Renaming Bones (original -> new name)
# ---------------------------
#
# Rename them to whatever you prefer, even add more following the template! 
# 
# Single bones: "old_bone": "new_name",
# For bones with direction: "old_bone_*:": "new_name*", (* replaces it with either .R or .L depending on the original name of the bone.)

RENAMING_RULES = {

# Body

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

# Hands

    "n_sude_*": "LowerArm*",
    "n_ste_*": "Wrist",
    "kl_te_*": "Hand",
    "nl_oya_*": "Thumb",
    "nl_hito_*": "Index",
    "nl_naka_*": "Middle",
    "nl_kusu_*": "Ring",
    "nl_ko_*": "Pinky",

# Head

    "n_eye_*": "Eye",
    "kl_ago_": "Jaw",

# Face
    
    "tl_mabu_*_d": "Lower_Eyelid*",
    "tl_mabu_*_u": "Upper_Eyelid*",
    "tl_mayu*": "Brow*",
    "tl_kuti_u_*": "Mouth_Upper*",
    "tl_kuti_d_*": "Mouth_Lower*",
    "tl_kuti_ds_*": "Lip_Corner*",
    "tl_eyelid_*": "Eyefold*", 
    "tl_tooth_upper": "Upper_Teeth"
}


# ---------------------------
# Reparenting rules (child -> parent)
# ---------------------------
#
# Some things should be already parented from the start, so hopefully this thing doesn't mess with them. 
# 
# Adding more rules following this format: "Child": "Parent", 
# Add the * at the end for direction bones. 
#

REPARENT_RULES = {

# Main Body
    "Head": "Neck",
    "Neck": "UpperChest",
    "UpperChest": "Chest",
    "Chest": "Spine",
    "Spine": "Hips",

# Arms

    "Shoulder*": "UpperChest",
    "UpperArm*": "Shoulder*",
    "LowerArm*": "UpperArm*",
    "Wrist*": "LowerArm*",
    "Hand*": "Wrist*", 

# Legs

   "UpperLeg*": "Hips",
   "Knee*": "UpperLeg*",
   "LowerLeg*": "UpperLeg*",
   "Knee*": "LowerLeg*",
   "Foot*": "LowerLeg*",
   "Toe*": "Foot*",

# Extra rules

   "UpperLeg_Extra*": "UpperLeg*",


}



### ACTUAL CODE SECTION (NOT RECCOMENDED TO MESS WITH) ###

# ---------------------------
# Bone Rename
# ---------------------------
# Quickly renames the bones according to the list above.  

def translate_bone_name(old_name: str) -> str:
    name = old_name.lower()

    for jp, en in RENAMING_RULES.items():
        if "*" in jp:  # side-dependent
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
    return old_name  # fallback: unchanged


# ---------------------------
# Reparent function
# ---------------------------
# Reparents bones based on REPARENT_RULES while preserving offsets
# and handling numbered duplicates (.001, .002, etc.).
# Works in Edit Mode. Does not snap child bones to parent.

import re
import bpy

def reparent_bones(arm):

    if arm is None or arm.type != "ARMATURE":
        return

    bpy.ops.object.mode_set(mode='EDIT')
    ebones = arm.data.edit_bones

    # helper maps for case-insensitive lookups
    lower_to_actual = {b.name.lower(): b.name for b in ebones}

    def is_numbered(bname):
        # matches a trailing ".123" numeric suffix
        return bool(re.search(r'\.\d+$', bname))

    def strip_number(bname):
        return re.sub(r'\.\d+$', '', bname)

    # Sort rules by key length (descending) so more specific rules win first:
    sorted_rules = sorted(REPARENT_RULES.items(), key=lambda kv: -len(kv[0]))

    # rule-based parenting
    for child_pattern, parent_pattern in sorted_rules:
        child_base_pattern = child_pattern.replace('*', '').lower()
        for eb in list(ebones):
            name = eb.name
            if is_numbered(name):
                continue  # handle numeric bones in pass 2

            lname = name.lower()

            # match child pattern
            matched = False
            if '*' in child_pattern:
                if child_base_pattern in lname:
                    matched = True
            else:
                if lname == child_pattern.lower():
                    matched = True

            if not matched:
                continue

            # Build parent candidate from parent_pattern, preserving side (.L/.R) if present
            parent_base = parent_pattern.replace('*', '')
            side = ''
            if name.endswith('.L') or name.endswith('.R'):
                side = name[-2:]  # ".L" or ".R"

            p_candidate = parent_base + side

            # find actual parent name (case-insensitive fallback)
            parent_actual = p_candidate if p_candidate in ebones else lower_to_actual.get(p_candidate.lower())
            if not parent_actual:
                # try parent without side (maybe parent has no side)
                parent_actual = parent_base if parent_base in ebones else lower_to_actual.get(parent_base.lower())
            if not parent_actual:
                # parent not found in armature; skip
                continue

            # avoid parenting a bone to itself
            if parent_actual == name:
                continue

            # preserve world-space head/tail
            head_world = arm.matrix_world @ eb.head
            tail_world = arm.matrix_world @ eb.tail

            eb.parent = ebones[parent_actual]
            eb.use_connect = False

            eb.head = arm.matrix_world.inverted() @ head_world
            eb.tail = arm.matrix_world.inverted() @ tail_world

            # Uncomment for debug:
            # print(f"RULE: Parented '{name}' -> '{parent_actual}'")

    # Group numeric duplicates and chain them under their exact base name
    grouped = {}
    for eb in ebones:
        if is_numbered(eb.name):
            base = strip_number(eb.name)  # keeps everything else, e.g. "UpperLeg_extra.L"
            grouped.setdefault(base, []).append(eb.name)

    for base_name, dup_list in grouped.items():
        # find actual base bone (case-insensitive)
        actual_base = base_name if base_name in ebones else lower_to_actual.get(base_name.lower())
        # sort duplicates by numeric suffix (1,2,3...)
        def num_key(n):
            try:
                return int(n.rsplit('.', 1)[1])
            except Exception:
                return 0
        dup_list.sort(key=num_key)

        prev = actual_base  # first child will parent to actual_base if present, otherwise chain among themselves
        for dup_name in dup_list:
            if dup_name not in ebones:
                continue
            eb = ebones[dup_name]

            # If there's no base but there are duplicates, chain them together (first dup will have no base parent).
            if prev is None:
                # set prev to the first duplicate and continue (no parent to assign)
                prev = dup_name
                continue

            # skip if prev == dup_name (shouldn't happen but safe-guard)
            if prev == dup_name:
                prev = dup_name
                continue

            head_world = arm.matrix_world @ eb.head
            tail_world = arm.matrix_world @ eb.tail

            eb.parent = ebones[prev]
            eb.use_connect = False

            eb.head = arm.matrix_world.inverted() @ head_world
            eb.tail = arm.matrix_world.inverted() @ tail_world

            # Uncomment for debug:
            # print(f"CHAIN: Parented '{dup_name}' -> '{prev}'")

            prev = dup_name

    bpy.ops.object.mode_set(mode='OBJECT')



# Rename
class BONE_OT_rename(bpy.types.Operator):
    """Rename bones"""
    bl_idname = "bone.rename"
    bl_label = "Rename Bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm = context.object
        if not arm or arm.type != "ARMATURE":
            self.report({"ERROR"}, "Select an Armature to rename bones.")
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

# Reparent
class BONE_OT_reparent(bpy.types.Operator):
    """Reparent bones"""
    bl_idname = "bone.reparent"
    bl_label = "Reparent Bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm = context.object
        if not arm or arm.type != "ARMATURE":
            self.report({"ERROR"}, "Select an Armature to reparent bones.")
            return {'CANCELLED'}
        
        reparent_bones(arm)
        self.report({"INFO"}, "Bones reparented based on rules.")
        return {'FINISHED'}


class BONE_PT_panel(bpy.types.Panel):
    """UI panel in Sidebar"""
    bl_label = "BoneMD"
    bl_idname = "BONE_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BoneMD"

    def draw(self, context):
        layout = self.layout

        # Info box at the top
        box = layout.box()
        box.label(text="BoneMD Tool", icon="INFO")
        box.label(text="Use this tool to rename Project Diva bone names into Unity-ready names.")
        box.label(text="Make sure your Armature is selected before pressing the button.")

        layout.separator()

        # Buttons
        layout.operator("bone.rename", icon="OUTLINER_OB_ARMATURE")
        
        box.label(text="Make sure to rename AND then reorder! ", icon="ERROR")
        box.label(text="Some bones will need to be reparented for some situations like legs.")

        layout.operator("bone.reparent", icon="OUTLINER_OB_ARMATURE")

        layout.separator()

        # Funny text
        credit = layout.box()
        credit.label(text="Made by Wealver", icon="USER") # Keep this unchanged, please!
        credit.label(text="Some bone names are model spesific with skirts and hair, this renames all the main reacuring bones for now!", icon="ERROR")
        credit.label(text="If there are any issues, message me.", icon="HEART")


# Registration
classes = (BONE_OT_rename, BONE_OT_reparent, BONE_PT_panel)

def register():
    for c in classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
