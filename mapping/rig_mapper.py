import numpy as np
from typing import Dict, List, Any, Optional

class RigMapper:
    """
    Handles mapping of Mixamo bone names to target skeletal structures
    and retargeting of animation data.
    """

    # Standard Mixamo bone names for reference
    MIXAMO_BONE_NAMES = [
        "mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Spine2",
        "mixamorig:Neck", "mixamorig:Head", "mixamorig:LeftShoulder", "mixamorig:LeftArm",
        "mixamorig:LeftForeArm", "mixamorig:LeftHand", "mixamorig:RightShoulder",
        "mixamorig:RightArm", "mixamorig:RightForeArm", "mixamorig:RightHand",
        "mixamorig:LeftUpLeg", "mixamorig:LeftLeg", "mixamorig:LeftFoot",
        "mixamorig:LeftToeBase", "mixamorig:RightUpLeg", "mixamorig:RightLeg",
        "mixamorig:RightFoot", "mixamorig:RightToeBase"
    ]

    def __init__(self, target_bone_names: List[str]):
        """
        Initializes the RigMapper with the target skeleton's bone names.

        Args:
            target_bone_names: A list of bone names in the target skeleton.
        """
        self.target_bone_names = target_bone_names
        self.mapping: Dict[str, str] = {}
        self._auto_map()

    def _auto_map(self):
        """
        Attempts to automatically map Mixamo bones to target bones based on name similarity.
        Refined heuristic: uses exact match after normalization and prevents loose partial matches.
        """
        # Common bone name components for normalization
        replacements = {
            "left": "l", "right": "r", "arm": "arm", "leg": "leg", "hand": "hand",
            "foot": "foot", "spine": "spine", "neck": "neck", "head": "head",
            "forearm": "forearm", "upleg": "upleg", "shoulder": "shoulder"
        }

        def normalize(name: str) -> str:
            # Remove all separators and common prefixes
            name = name.lower().replace("_", "").replace(" ", "").replace("-", "")
            name = name.split(":")[-1] # Remove prefixes like 'mixamorig:' or 'armature:'
            for old, new in replacements.items():
                name = name.replace(old, new)
            return name

        # Map by normalized exact match first
        for mixamo_bone in self.MIXAMO_BONE_NAMES:
            mixamo_norm = normalize(mixamo_bone)
            for target_bone in self.target_bone_names:
                if normalize(target_bone) == mixamo_norm:
                    self.mapping[mixamo_bone] = target_bone
                    break
        
        # Second pass: if a Mixamo bone is still unmapped, use a more conservative partial match
        for mixamo_bone in self.MIXAMO_BONE_NAMES:
            if mixamo_bone in self.mapping:
                continue
            
            mixamo_norm = normalize(mixamo_bone)
            for target_bone in self.target_bone_names:
                target_norm = normalize(target_bone)
                # Ensure it's not already mapped to another Mixamo bone
                if target_bone in self.mapping.values():
                    continue
                
                # Check for conservative containment (e.g., 'larm' in 'lowerlarm')
                if (mixamo_norm in target_norm or target_norm in mixamo_norm) and len(mixamo_norm) > 2:
                    self.mapping[mixamo_bone] = target_bone
                    break

    def set_custom_mapping(self, mapping: Dict[str, str]):
        """
        Sets a custom mapping of Mixamo bone names to target bone names.

        Args:
            mapping: A dictionary where keys are Mixamo bone names and values are target bone names.
        """
        for mixamo_bone, target_bone in mapping.items():
            if target_bone in self.target_bone_names:
                self.mapping[mixamo_bone] = target_bone

    def get_mapping(self) -> Dict[str, str]:
        """
        Returns the current bone mapping.

        Returns:
            Dict[str, str]: The current mapping.
        """
        return self.mapping

    def retarget_animation(self, animation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retargets animation data from Mixamo bones to target bones.

        Args:
            animation_data: A dictionary where keys are Mixamo bone names and values are
                           animation transforms (e.g., 4x4 matrices).

        Returns:
            Dict[str, Any]: A dictionary where keys are target bone names and values
                                  are the retargeted transforms.
        """
        retargeted_data = {}
        for mixamo_bone, transform in animation_data.items():
            if mixamo_bone in self.mapping:
                target_bone = self.mapping[mixamo_bone]
                retargeted_data[target_bone] = transform
        return retargeted_data

    def apply_to_scene(self, scene: Any, animation_data: Dict[str, Any]):
        """
        Applies retargeted animation data to a trimesh Scene graph.

        Args:
            scene: The trimesh Scene to apply the animation to.
            animation_data: The Mixamo animation data to retarget and apply.
        """
        retargeted_data = self.retarget_animation(animation_data)
        for bone_name, transform in retargeted_data.items():
            if bone_name in scene.graph.nodes:
                # trimesh.Scene.graph.update updates the transform of a node
                scene.graph.update(bone_name, matrix=transform)
