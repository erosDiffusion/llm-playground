#!/usr/bin/env python3
"""
FFmpeg version check and upgrade helper for video-scene-extractor skill.

This script checks ffmpeg installation, verifies lavfi filter support,
and provides upgrade instructions if needed.
"""

import subprocess
import sys


def check_ffmpeg():
    """Check if ffmpeg is installed and compatible."""
    print("=" * 60)
    print("FFmpeg Version Check")
    print("=" * 60)
    
    # Check if ffmpeg exists
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        version_output = result.stdout
        
        print("\n✓ FFmpeg is installed")
        print()
        
        # Parse version line
        for line in version_output.split('\n'):
            if 'version' in line.lower():
                print(f"Version: {line.strip()}")
        
        # Check lavfi support - try multiple methods
        has_lavfi = False
        
        # Method 1: Check filters help
        try:
            result = subprocess.run(['ffmpeg', '-h', 'filters'], 
                                  capture_output=True, text=True, timeout=5)
            if 'lavfi' in result.stdout.lower() or 'lavfilter' in result.stdout.lower():
                has_lavfi = True
        except:
            pass
        
        # Method 2: Check build configuration for lavfi enable
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        config_line = [line for line in result.stdout.split('\n') if 'enable-lavfi' in line.lower()][0] if 'enable-lavfi' in result.stdout else ""
        
        # Method 3: Check configuration for lavfi enable (most reliable)
        config_lines = [line for line in result.stdout.split('\n') 
                       if 'enable-lavfi' in line.lower() and '--enable-lavfi' in line]
        
        # If --enable-lavfi is in the build configuration, lavfi is available
        if config_lines:
            has_lavfi = True
        
        # Method 4: Verify by attempting to use a filter (scdet)
        if not has_lavfi:
            try:
                test_cmd = ['ffmpeg', '-h', 'scdet']
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    has_lavfi = True
            except Exception as e:
                pass
        
        if has_lavfi:
            print("✓ lavfi filter support: AVAILABLE")
        else:
            print("✗ lavfi filter support: NOT FOUND")
            print("\n⚠ CRITICAL: The video-scene-extractor skill requires lavfi filter.")
            print("   Without it, scdet detection will fail.")
            
            # Provide upgrade instructions
            print("\n" + "=" * 60)
            print("UPGRADE INSTRUCTIONS")
            print("=" * 60)
            print()
            print("The current ffmpeg build is missing lavfi support. This is common in")
            print("hardened Ubuntu packages. You need to install a full ffmpeg package.")
            print()
            print("Ubuntu/Debian:")
            print("  sudo apt-get update")
            print("  sudo apt-get install -y ffmpeg")
            print()
            print("Or download from official FFmpeg website:")
            print("  https://ffmpeg.org/download.html#build-dependencies")
            print()
            print("Conda (recommended):")
            print("  conda create -n ffmpeg-env python=3.10 ffmpeg=6.1.1")
            print("  conda run -n ffmpeg-env python3 scripts/check_ffmpeg.py")
            
    except FileNotFoundError:
        print("✗ FFmpeg is NOT installed on this system")
        print()
        print("Install instructions:")
        print("  # Ubuntu/Debian:")
        print("  apt-get update && apt-get install -y ffmpeg")
        print()
        print("  # macOS (brew):")
        print("  brew install ffmpeg")
        print()
        print("  # Conda:")
        print("  conda install ffmpeg=6.1.1")
        
    except subprocess.TimeoutExpired:
        print("✗ FFmpeg check timed out")
    
    return True


def get_ffmpeg_version():
    """Get the ffmpeg version string."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if 'version' in line.lower() and 'lavf' not in line.lower():
                return line.strip()
    except:
        pass
    return "unknown"


def check_script_compatibility():
    """Check if current ffmpeg supports the features the pipeline actually uses.

    v2: the old probe grepped `ffmpeg -h formats` for '-lavfi' — that option never
    appears there, so the check failed on ffmpeg 6.1.1, the very version the skill
    requires, and told users to upgrade a working install. The pipeline uses scdet
    as a -vf filter (plus select/metadata), not the -lavfi input flag. Test that.
    """
    print("\n" + "=" * 60)
    print("Script Compatibility Check")
    print("=" * 60)

    try:
        result = subprocess.run(['ffmpeg', '-hide_banner', '-filters'],
                              capture_output=True, text=True, timeout=10)
        need = ["scdet", "select", "metadata", "scale"]
        missing = [f for f in need
                   if not any(f" {f} " in ln for ln in result.stdout.splitlines())]
        if not missing:
            print("✓ required filters (scdet, select, metadata, scale): SUPPORTED")
        else:
            print(f"✗ missing filters: {', '.join(missing)}")
            print("\n⚠ scdet is the scene-score pass (skill step 2a); without it that pass fails.")
            print("   The MAD pass (2b) still works — the pipeline degrades, not dies.")

    except Exception as e:
        print(f"Could not check script compatibility: {e}")


def main():
    """Main entry point."""
    check_ffmpeg()
    version = get_ffmpeg_version()
    print(f"\nCurrent ffmpeg version: {version}")
    
    # If no version info found, warn user
    if "unknown" in str(version):
        print("\n⚠ Could not determine ffmpeg version. Please ensure ffmpeg is properly installed.")
    
    check_script_compatibility()
    
    print("\n" + "=" * 60)
    print("Check Complete")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
