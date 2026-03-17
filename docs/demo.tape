# Agent Usage Atlas — Demo Recording
# Install vhs first: brew install vhs
# Run: vhs docs/demo.tape

Output docs/screenshots/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 60ms

# Title
Type "# Agent Usage Atlas — One command, full dashboard"
Enter
Sleep 1s

# Install
Type "pip install agent-usage-atlas"
Enter
Sleep 3s

# Run
Type "agent-usage-atlas --days 30 --open"
Enter
Sleep 5s

# Show output
Type "# Dashboard generated! Opening in browser..."
Enter
Sleep 3s
