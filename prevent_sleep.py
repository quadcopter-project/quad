import time
import pyautogui

def prevent_sleep():
    # Move the mouse slightly
    pyautogui.moveRel(1, 1)

def main():
    try:
        while True:
            prevent_sleep()
            # Wait for 10 minute before moving the mouse again
            time.sleep(600)  
    except KeyboardInterrupt:
        print("Script stopped.")

if __name__ == "__main__":
    main()