# Interactive Annotation Tool Guide

## Quick Start

Start annotating your Lady Gaga comments right away:

```bash
python scripts/interactive_annotator.py "data/training_data_habpdmFSTOo_Lady Gaga on Double Standards _20250909_190009.csv"
```

## How It Works

### 🎯 Main Interface
For each comment, you'll see:
- **Author info**: Username, likes, date, reply status
- **Text features**: Word count, punctuation, capitalization
- **Comment text**: The actual comment to annotate
- **Choice menu**: Simple keyboard shortcuts

### ⌨️ Keyboard Shortcuts
- **[p]** - Positive sentiment
- **[n]** - Negative sentiment  
- **[z]** - Neutral sentiment
- **[s]** - Skip this comment (come back later)
- **[b]** - Go back to previous comment
- **[q]** - Quit and save all progress
- **[?]** - Show help guide

### 📊 Annotation Flow
1. **Choose sentiment** (p/n/z)
2. **Rate intensity** (for positive/negative: 1=somewhat, 2=very)
3. **Set confidence** (1-5, default=4)
4. **Add notes** (optional)

## Features

### 🔄 Smart Resume
- Automatically finds the first unannotated comment
- Shows your progress (e.g., "Resuming from comment #45")
- Never lose your work

### 💾 Auto-Save & Backup
- Creates backup file on first save (`*.backup.csv`)
- Saves progress after every annotation
- Safe to quit anytime with Ctrl+C

### 📈 Progress Tracking
- Shows completion percentage
- Progress updates every 10 annotations
- Final summary with sentiment distribution

### 🏃‍♀️ Navigation
- Move forward/backward through comments
- Skip difficult ones and come back later
- Jump to help anytime

## Example Session

```
📝 Comment #1 of 183
================================================================================
👤 Author: @Benleyy
👍 Likes: 379
📅 Date: 2020-12-31 04:56:41
💬 Reply: No

💭 COMMENT TEXT:
"She breathes and its iconic- every interview she has is legendary"

🎯 Choose sentiment: p
📊 How positive? [1] Somewhat positive  [2] Very positive
Score (default=1): 2
Confidence 1-5 (default=4): 5
Notes (optional): 
✅ Annotated as positive
```

## Tips for Success

### 🎯 Consistency Strategy
1. **Start small**: Do 20-30 comments to establish your standards
2. **Take breaks**: Annotate in 30-60 minute sessions
3. **Use notes**: Write down reasoning for complex cases
4. **Trust defaults**: Default scores (1 for pos/neg, 4 for confidence) work well

### 🤔 Handling Tricky Comments
- **Mixed sentiment**: Choose neutral, add note explaining why
- **Sarcasm**: Annotate the intended sentiment, add note
- **Foreign language**: Skip or mark as neutral with note
- **Unclear context**: Lower confidence score, add note

### ⚡ Speed Tips
- **Use defaults**: Just press Enter for default scores
- **Quick keys**: p/n/z are faster than typing full words
- **Skip tough ones**: Come back later when you're fresh

## Command Line Options

```bash
# Basic usage
python scripts/interactive_annotator.py data/your_file.csv

# Get help
python scripts/interactive_annotator.py --help
```

## File Safety

The tool is designed to be safe:
- ✅ **Creates backups** before modifying files
- ✅ **Saves frequently** (after each annotation)
- ✅ **Handles interruptions** gracefully (Ctrl+C)
- ✅ **Preserves original data** (no data loss)

## Sample Workflow

### Day 1: Initial Setup (15 min)
1. Run the tool
2. Annotate 20-30 comments
3. Establish your personal standards
4. Save and review your consistency

### Ongoing: Regular Sessions (30-60 min)
1. Resume where you left off
2. Annotate 50-100 comments per session
3. Take breaks between sessions
4. Use progress tracking to stay motivated

### Final: Quality Check
1. Review final summary statistics
2. Spot-check some annotations
3. Your training data is ready!

---

**Happy Annotating! 🎉**

Remember: The goal is consistent, thoughtful labels that will help your model learn patterns. Don't stress about perfect decisions - consistency matters more than perfection!
