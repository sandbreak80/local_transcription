#!/usr/bin/env python3
"""
Test script for animated quote detection functionality.
This script demonstrates how to use the animated quote detection feature.
"""

import os
import sys
from pathlib import Path
from transcribe import MediaTranscriber
from animated_quotes import AnimatedQuoteDetector


def test_animated_quote_detection():
    """Test the animated quote detection functionality."""
    print("Testing Animated Quote Detection")
    print("=" * 50)
    
    # Initialize transcriber
    transcriber = MediaTranscriber(model_size="base")
    
    # Test file path (replace with your actual file)
    test_file = "test_audio.mp3"
    
    if not os.path.exists(test_file):
        print(f"Test file '{test_file}' not found.")
        print("Please provide a test audio/video file to test the animated quote detection.")
        print("\nTo test with your own file:")
        print("1. Place an audio/video file in this directory")
        print("2. Update the 'test_file' variable in this script")
        print("3. Run: python test_animated_quotes.py")
        return
    
    try:
        print(f"Processing file: {test_file}")
        print("This may take a few minutes depending on file size and model...")
        
        # Detect animated quotes
        result = transcriber.detect_animated_quotes(
            test_file, 
            quote_duration=15.0, 
            num_quotes=10
        )
        
        print(f"\nTranscription completed!")
        print(f"Language: {result['language']}")
        print(f"Total segments: {len(result['segments'])}")
        
        # Display results
        if result.get('animated_quotes'):
            print(f"\nFound {len(result['animated_quotes'])} animated quotes:")
            print("-" * 60)
            
            for i, quote in enumerate(result['animated_quotes'], 1):
                start_time = transcriber.quote_detector.format_timestamp(quote.start_timestamp)
                end_time = transcriber.quote_detector.format_timestamp(quote.end_timestamp)
                
                print(f"\n{i}. [{start_time} - {end_time}] ({quote.topic_category})")
                print(f"   Animatedness Score: {quote.animatedness_score:.3f}")
                print(f"   Text: {quote.text}")
            
            # Save results
            transcriber.save_transcription(result, "test_output/")
            transcriber.save_animated_quotes(result, "test_output/")
            
            # Show topic distribution
            topic_counts = {}
            for quote in result['animated_quotes']:
                topic_counts[quote.topic_category] = topic_counts.get(quote.topic_category, 0) + 1
            
            print(f"\nTopic Distribution:")
            for topic, count in topic_counts.items():
                print(f"  {topic.replace('_', ' ').title()}: {count} quotes")
            
            print(f"\nResults saved to 'test_output/' directory")
        else:
            print("No animated quotes detected.")
            print("This could be due to:")
            print("- Low audio quality")
            print("- Monotone speech")
            print("- Very short audio file")
            print("- No segments with sufficient animatedness")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure the file format is supported")
        print("2. Check that all dependencies are installed")
        print("3. Try with a different audio/video file")


def test_topic_classification():
    """Test the topic classification functionality."""
    print("\nTesting Topic Classification")
    print("=" * 50)
    
    detector = AnimatedQuoteDetector()
    
    # Test sentences for each topic
    test_sentences = [
        "We currently have AI technology deployed in production across our network infrastructure.",
        "The future of AI at enterprise will revolutionize how we approach network management.",
        "We have several new AI products coming on the truck next quarter that will change everything.",
        "Our existing machine learning models are already showing incredible results.",
        "The roadmap for next year includes breakthrough innovations in artificial intelligence.",
        "What's in our product pipeline includes next-generation AI solutions for enterprise customers."
    ]
    
    for sentence in test_sentences:
        topic = detector.classify_topic(sentence)
        print(f"Text: {sentence}")
        print(f"Classified as: {topic.replace('_', ' ').title()}")
        print("-" * 40)


def test_timestamp_formatting():
    """Test timestamp formatting functionality."""
    print("\nTesting Timestamp Formatting")
    print("=" * 50)
    
    detector = AnimatedQuoteDetector()
    
    test_times = [0, 15.5, 90.25, 3661.123, 7200.0]
    
    for time in test_times:
        formatted = detector.format_timestamp(time)
        print(f"{time:8.3f} seconds -> {formatted}")


if __name__ == "__main__":
    print("Animated Quote Detection Test Suite")
    print("=" * 50)
    
    # Run tests
    test_topic_classification()
    test_timestamp_formatting()
    test_animated_quote_detection()
    
    print("\n" + "=" * 50)
    print("Test suite completed!")
    print("\nTo use the animated quote detection feature:")
    print("python transcribe.py your_file.mp3 --animated-quotes")

