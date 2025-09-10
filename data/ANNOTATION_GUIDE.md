# Sentiment Annotation Guide

## Overview
This guide helps you consistently annotate comments for sentiment analysis training data. The goal is to create high-quality labeled data that the machine learning model can learn from.

## Key Annotation Columns

### 1. sentiment_label
**Values:** `positive`, `negative`, `neutral`

- **positive**: Comments expressing satisfaction, praise, agreement, joy, or other positive emotions
- **negative**: Comments expressing dissatisfaction, criticism, anger, sadness, or other negative emotions  
- **neutral**: Comments that are factual, questions, or don't express clear sentiment

### 2. sentiment_score
**Scale:** -2 to +2 (integer values only)

- **+2**: Very positive (enthusiastic praise, love, excitement)
- **+1**: Somewhat positive (mild praise, agreement, satisfaction)
- **0**: Neutral (factual statements, questions, mixed sentiment)
- **-1**: Somewhat negative (mild criticism, disappointment, concern)
- **-2**: Very negative (strong criticism, anger, hate, disgust)

### 3. emotion_primary
**Values:** `joy`, `anger`, `fear`, `sadness`, `surprise`, `disgust`, `neutral`

Choose the dominant emotion expressed in the comment:
- **joy**: Happiness, excitement, amusement
- **anger**: Frustration, rage, irritation
- **fear**: Worry, anxiety, concern
- **sadness**: Disappointment, melancholy, grief
- **surprise**: Shock, amazement (can be positive or negative)
- **disgust**: Revulsion, strong disapproval
- **neutral**: No clear emotional expression

### 4. confidence
**Scale:** 1-5

Rate how confident you are in your annotation:
- **5**: Very confident - clear, unambiguous sentiment
- **4**: Confident - sentiment is clear with minor ambiguity
- **3**: Moderately confident - some ambiguity but leaning toward one sentiment
- **2**: Low confidence - ambiguous, could go either way
- **1**: Very low confidence - extremely difficult to determine

## Context Flags

### is_sarcastic
**Values:** 1 (sarcastic) or 0 (not sarcastic)
- Mark as 1 if the comment uses sarcasm or irony
- This helps the model learn to detect indirect sentiment

### is_spam
**Values:** 1 (spam) or 0 (not spam)
- Mark as 1 for promotional content, nonsensical text, or repeated messages

### is_off_topic
**Values:** 1 (off-topic) or 0 (on-topic)
- Mark as 1 if the comment is unrelated to the video content

### language_other
**Values:** 1 (not English) or 0 (English)
- Mark as 1 if the comment is primarily in a language other than English

## Annotation Tips

### Handle Ambiguity
- When in doubt, lean toward **neutral** for sentiment_label
- Use confidence score to indicate uncertainty
- Add notes for complex cases

### Consider Context
- The comment's relationship to the video topic
- Response to other comments (if it's a reply)
- Cultural or contextual references

### Be Consistent
- Develop your own internal standards and stick to them
- Review your first 20-30 annotations to establish consistency
- Take breaks to avoid fatigue-induced inconsistency

### Common Edge Cases

#### Mixed Sentiment
```
"I love Lady Gaga but I hate this interviewer"
```
- sentiment_label: `neutral` (mixed emotions cancel out)
- sentiment_score: `0`
- notes: "Mixed: positive about Gaga, negative about interviewer"

#### Sarcasm
```
"Oh great, another feminist rant..."
```
- sentiment_label: `negative`
- sentiment_score: `-1`
- is_sarcastic: `1`

#### Questions
```
"What song is she talking about at 2:30?"
```
- sentiment_label: `neutral`
- sentiment_score: `0`
- emotion_primary: `neutral`

#### Factual Statements
```
"This was filmed in 2012"
```
- sentiment_label: `neutral`
- sentiment_score: `0`
- emotion_primary: `neutral`

## Quality Control

### Before You Start
1. Read through 10-20 comments to get a feel for the content
2. Practice with a few examples to establish your standards
3. Keep this guide handy for reference

### During Annotation
1. Work in batches of 50-100 comments
2. Take breaks between batches
3. Re-read comments that seem ambiguous
4. Use the notes field for complex cases

### After Completion
1. Review a random sample of your annotations
2. Look for patterns in your confidence scores
3. Consider revisiting low-confidence annotations

## Example Annotations

| Comment | sentiment_label | sentiment_score | emotion_primary | confidence | notes |
|---------|----------------|-----------------|-----------------|------------|-------|
| "Love her so much! She's amazing ❤️" | positive | +2 | joy | 5 | Clear positive with emotion |
| "She makes some good points here" | positive | +1 | neutral | 4 | Mild agreement |
| "This is just her opinion, nothing more" | neutral | 0 | neutral | 4 | Factual/dismissive but not negative |
| "I disagree with her stance on this" | negative | -1 | neutral | 4 | Polite disagreement |
| "What a load of garbage. Unsubscribing!" | negative | -2 | anger | 5 | Strong negative reaction |

Remember: The goal is to create training data that will help a machine learn to recognize sentiment patterns. Consistency is more important than perfection!
