import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def simple_conversion_test():
    """Simple test for DNG/CR2 to JPG conversion"""
    
    # Get network path
    NETWORK_PATH = os.getenv("NETWORK_PATH")
    if not NETWORK_PATH:
        print("❌ NETWORK_PATH environment variable not set!")
        return False
    
    if not os.path.exists(NETWORK_PATH):
        print(f"❌ Network path does not exist: {NETWORK_PATH}")
        return False
    
    print(f"📂 Using: {NETWORK_PATH}")
    
    # ImageMagick path
    magick_path = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
    
    if not os.path.exists(magick_path):
        print("❌ ImageMagick not found!")
        return False
    
    # Look for DNG/CR2 files in main directory only
    network_dir = Path(NETWORK_PATH)
    raw_files = list(network_dir.glob('*.DNG')) + list(network_dir.glob('*.dng')) + \
                list(network_dir.glob('*.CR2')) + list(network_dir.glob('*.cr2'))
    
    if not raw_files:
        print("❌ No DNG or CR2 files found in the main directory")
        return False
    
    print(f"📸 Found {len(raw_files)} RAW files:")
    for f in raw_files:
        print(f"  - {f.name}")
    
    # Convert ALL RAW files
    success_count = 0
    total_count = len(raw_files)
    
    for test_file in raw_files:
        jpg_path = test_file.with_suffix('.jpg').with_stem(f"{test_file.stem}_converted")
        
        print(f"\n🔄 Converting: {test_file.name} → {jpg_path.name}")
        
        # Convert
        cmd = [magick_path, str(test_file), '-quality', '95', str(jpg_path)]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and jpg_path.exists():
                print("✅ Conversion successful!")
                
                # Show file sizes
                raw_size = test_file.stat().st_size / (1024*1024)
                jpg_size = jpg_path.stat().st_size / (1024*1024)
                print(f"📊 RAW: {raw_size:.1f}MB → JPG: {jpg_size:.1f}MB")
                success_count += 1
            else:
                print(f"❌ Conversion failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n📊 Conversion Summary:")
    print(f"✅ Successfully converted: {success_count}/{total_count} files")
    
    return success_count > 0

if __name__ == "__main__":
    print("🚀 Simple RAW to JPG Test")
    print("-" * 30)
    
    if simple_conversion_test():
        print("\n✅ Ready to convert all RAW files!")
    else:
        print("\n❌ Fix issues before proceeding")