#!/usr/bin/env python3
"""
Debug script to test slider functionality and identify common issues.

This script will help identify what might be causing sliders to not work consistently.
"""
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def check_slider_html_structure():
    """Check the HTML structure of sliders in templates."""
    print("=== Checking Slider HTML Structure ===")
    
    template_path = Path("app/templates/analyze.html")
    if not template_path.exists():
        print("❌ Template file not found")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for slider elements
    sliders_found = []
    
    # Check for unifiedSlider
    if 'id="unifiedSlider"' in content:
        sliders_found.append("unifiedSlider")
        print("✓ Found unifiedSlider")
    
    # Check for range inputs
    import re
    range_inputs = re.findall(r'<input[^>]*type=["\']range["\'][^>]*>', content)
    print(f"✓ Found {len(range_inputs)} range inputs")
    
    # Check for event listeners
    if 'addEventListener' in content:
        event_listeners = re.findall(r'\.addEventListener\(["\'](\w+)["\']', content)
        print(f"✓ Found event listeners: {set(event_listeners)}")
    
    # Check for slider-related JavaScript functions
    js_functions = []
    if 'updateUnifiedUI' in content:
        js_functions.append("updateUnifiedUI")
    if 'configureSliderForUser' in content:
        js_functions.append("configureSliderForUser")
    if 'setupRangeIndicatorClicks' in content:
        js_functions.append("setupRangeIndicatorClicks")
    
    print(f"✓ Found JavaScript functions: {js_functions}")
    
    return len(sliders_found) > 0

def check_slider_css():
    """Check CSS styling for sliders."""
    print("\n=== Checking Slider CSS ===")
    
    css_path = Path("app/static/css/vibecheckai.css")
    if not css_path.exists():
        print("❌ CSS file not found")
        return False
    
    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for slider styles
    css_classes = []
    
    if '.coverage-slider' in content:
        css_classes.append("coverage-slider")
        print("✓ Found .coverage-slider styles")
    
    if '.slider-container' in content:
        css_classes.append("slider-container")
        print("✓ Found .slider-container styles")
    
    if '.range-indicator' in content:
        css_classes.append("range-indicator")
        print("✓ Found .range-indicator styles")
    
    # Check for webkit and mozilla prefixes
    webkit_styles = content.count('-webkit-')
    moz_styles = content.count('-moz-')
    
    print(f"✓ Found {webkit_styles} webkit-specific styles")
    print(f"✓ Found {moz_styles} mozilla-specific styles")
    
    return len(css_classes) > 0

def check_common_slider_issues():
    """Check for common issues that cause sliders to malfunction."""
    print("\n=== Checking Common Slider Issues ===")
    
    issues_found = []
    
    template_path = Path("app/templates/analyze.html")
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Issue 1: Conflicting JavaScript
    if content.count('addEventListener') > 20:
        issues_found.append("Many event listeners - potential conflicts")
        print("⚠️  Found many event listeners - potential for conflicts")
    
    # Issue 2: Missing error handling
    if 'try {' not in content or content.count('catch') < 3:
        issues_found.append("Limited error handling in JavaScript")
        print("⚠️  Limited error handling in JavaScript")
    
    # Issue 3: DOM timing issues
    if 'DOMContentLoaded' not in content and 'document.ready' not in content:
        issues_found.append("No explicit DOM ready handling")
        print("⚠️  No explicit DOM ready handling found")
    
    # Issue 4: Check for async operations without proper handling
    if 'setTimeout' in content:
        timeout_count = content.count('setTimeout')
        print(f"ℹ️  Found {timeout_count} setTimeout calls - check timing")
    
    # Issue 5: Check for multiple slider initializations
    init_calls = content.count('configureSliderForUser')
    if init_calls > 1:
        issues_found.append(f"Multiple slider initializations ({init_calls})")
        print(f"⚠️  Found {init_calls} calls to configureSliderForUser")
    
    if not issues_found:
        print("✅ No obvious common issues found")
    
    return issues_found

def generate_slider_test_html():
    """Generate a minimal HTML file to test slider functionality."""
    print("\n=== Generating Slider Test File ===")
    
    test_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Slider Test</title>
    <style>
        .slider-container {
            margin: 20px;
            padding: 20px;
            border: 1px solid #ccc;
        }
        .coverage-slider {
            width: 100%;
            height: 8px;
            border-radius: 10px;
            background: linear-gradient(to right, #e2e8f0 0%, #6366f1 50%, #10b981 100%);
            outline: none;
            -webkit-appearance: none;
        }
        .coverage-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: white;
            border: 3px solid #6366f1;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .coverage-slider::-moz-range-thumb {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: white;
            border: 3px solid #6366f1;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .slider-values {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            font-size: 0.9rem;
            color: #6b7280;
        }
        .current-value {
            font-weight: 600;
            color: #6366f1;
        }
        .debug-info {
            margin-top: 20px;
            padding: 15px;
            background: #f3f4f6;
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <h1>Slider Functionality Test</h1>
    
    <div class="slider-container">
        <h3>Test Slider</h3>
        <input type="range" 
               class="coverage-slider" 
               id="testSlider" 
               min="5" 
               max="5000" 
               step="5" 
               value="1000">
        <div class="slider-values">
            <span id="sliderMin">5</span>
            <span class="current-value" id="sliderCurrent">1,000</span>
            <span id="sliderMax">5,000</span>
        </div>
        
        <div class="debug-info">
            <h4>Debug Information</h4>
            <p><strong>Value:</strong> <span id="debugValue">1000</span></p>
            <p><strong>Last Event:</strong> <span id="debugEvent">none</span></p>
            <p><strong>Event Count:</strong> <span id="debugEventCount">0</span></p>
            <p><strong>Browser:</strong> <span id="debugBrowser"></span></p>
            <p><strong>Touch Device:</strong> <span id="debugTouch"></span></p>
        </div>
    </div>
    
    <div class="slider-container">
        <h3>Manual Test</h3>
        <p>Try these actions:</p>
        <ul>
            <li>Click and drag the slider</li>
            <li>Click on the slider track</li>
            <li>Use arrow keys when focused</li>
            <li>Try on mobile/touch device</li>
        </ul>
        <button onclick="testSliderProgrammatically()">Set Slider to 2500</button>
        <button onclick="resetSlider()">Reset to 1000</button>
    </div>

    <script>
        let eventCount = 0;
        const slider = document.getElementById('testSlider');
        const currentDisplay = document.getElementById('sliderCurrent');
        const debugValue = document.getElementById('debugValue');
        const debugEvent = document.getElementById('debugEvent');
        const debugEventCount = document.getElementById('debugEventCount');
        const debugBrowser = document.getElementById('debugBrowser');
        const debugTouch = document.getElementById('debugTouch');
        
        // Detect browser and device info
        debugBrowser.textContent = navigator.userAgent.includes('Chrome') ? 'Chrome' : 
                                  navigator.userAgent.includes('Firefox') ? 'Firefox' : 
                                  navigator.userAgent.includes('Safari') ? 'Safari' : 'Other';
        debugTouch.textContent = 'ontouchstart' in window ? 'Yes' : 'No';
        
        function updateDisplay(value, eventType) {
            currentDisplay.textContent = parseInt(value).toLocaleString();
            debugValue.textContent = value;
            debugEvent.textContent = eventType;
            debugEventCount.textContent = ++eventCount;
            console.log(`Slider event: ${eventType}, value: ${value}`);
        }
        
        // Add multiple event listeners to catch all interactions
        slider.addEventListener('input', function(e) {
            updateDisplay(this.value, 'input');
        });
        
        slider.addEventListener('change', function(e) {
            updateDisplay(this.value, 'change');
        });
        
        slider.addEventListener('mousedown', function(e) {
            console.log('Slider mousedown');
        });
        
        slider.addEventListener('mouseup', function(e) {
            console.log('Slider mouseup');
        });
        
        slider.addEventListener('touchstart', function(e) {
            console.log('Slider touchstart');
        });
        
        slider.addEventListener('touchend', function(e) {
            console.log('Slider touchend');
        });
        
        // Test functions
        function testSliderProgrammatically() {
            slider.value = 2500;
            updateDisplay(slider.value, 'programmatic');
        }
        
        function resetSlider() {
            slider.value = 1000;
            updateDisplay(slider.value, 'reset');
        }
        
        // Initial display update
        updateDisplay(slider.value, 'initial');
        
        console.log('Slider test initialized');
    </script>
</body>
</html>"""
    
    test_file = Path("slider_test.html")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_html)
    
    print(f"✅ Created {test_file.absolute()}")
    print("   Open this file in your browser to test slider functionality")
    
    return str(test_file.absolute())

def suggest_fixes():
    """Suggest potential fixes for common slider issues."""
    print("\n=== Suggested Fixes ===")
    
    fixes = [
        {
            "issue": "Slider not responding to touch events",
            "fix": "Add touch-action: manipulation; to slider CSS"
        },
        {
            "issue": "Multiple event listeners causing conflicts",
            "fix": "Use event delegation or remove listeners before adding new ones"
        },
        {
            "issue": "Slider values not updating",
            "fix": "Ensure both 'input' and 'change' events are handled"
        },
        {
            "issue": "Timing issues with DOM elements",
            "fix": "Wrap slider initialization in DOMContentLoaded or setTimeout"
        },
        {
            "issue": "CSS conflicts with slider thumb",
            "fix": "Add !important to critical slider thumb styles"
        },
        {
            "issue": "JavaScript errors preventing slider updates",
            "fix": "Add try-catch blocks around slider update functions"
        }
    ]
    
    for i, fix in enumerate(fixes, 1):
        print(f"{i}. {fix['issue']}")
        print(f"   → {fix['fix']}")
        print()

def main():
    print("Slider Functionality Debug Tool")
    print("=" * 50)
    
    # Run diagnostics
    html_ok = check_slider_html_structure()
    css_ok = check_slider_css()
    issues = check_common_slider_issues()
    test_file = generate_slider_test_html()
    
    print("\n=== Summary ===")
    print(f"HTML Structure: {'✅ OK' if html_ok else '❌ Issues'}")
    print(f"CSS Styles: {'✅ OK' if css_ok else '❌ Issues'}")
    print(f"Common Issues: {len(issues)} found")
    
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    
    suggest_fixes()
    
    print(f"\n🧪 Test file created: {test_file}")
    print("\nNext steps:")
    print("1. Open the test file in your browser")
    print("2. Test slider functionality manually")
    print("3. Check browser console for JavaScript errors")
    print("4. Test on different devices/browsers")

if __name__ == "__main__":
    main()