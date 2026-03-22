# Initial Concept

Create an application that takes one parameter called model_name, a FBX model, and one parameter animation_name, the name of an animation, and creates a new model with that specific animation loaded from Mixamo motion animations. Mixamo motion animations can be found in https://www.mixamo.com/#/?page=1&type=Motion%2CMotionPack . Create the tool in python. Launch a window with the loaded new model and a list of all the animations it has, allowing to play the animations in the window.

---

# Product Definition: MixamoAnimator

## Vision
A desktop-based automation tool for hobbyist artists to effortlessly map Mixamo motion animations onto their custom FBX models and preview them in real-time.

## Target Audience
- **Hobbyist Artists:** Individuals looking for a simple, accessible way to animate their 3D characters without manual rigging or complex software.

## Core Features (MVP)
- **Animation Mapping:** Automated transfer of Mixamo motion data to user-provided FBX skeletal models.
- **Real-time Playback GUI:** A standalone PyQt/PySide-based desktop window for loading models, listing animations, and interactive playback.
- **Parametric Interface:** Simple command-line initialization with `model_name` and `animation_name` for rapid processing.

## Success Criteria
- Successful loading of a skinned FBX model.
- Accurate mapping of Mixamo animation data.
- Smooth, real-time animation playback in the GUI.
