from pathlib import Path

img_dir = Path(__file__).resolve().parent.parent / "static" / "img"
img_dir.mkdir(parents=True, exist_ok=True)

icons = {
    "bottle.svg": ("🥤", "#00d4aa", "Cold Drink"),
    "cup.svg": ("🍜", "#ffaa00", "Cup Noodles"),
    "banana.svg": ("🍌", "#ffd700", "Banana"),
    "apple.svg": ("🍎", "#ff4444", "Apple"),
    "orange.svg": ("🍊", "#ff8800", "Orange"),
    "phone.svg": ("📱", "#00bfff", "Smartphone"),
    "sandwich.svg": ("🥪", "#daa520", "Sandwich"),
    "cake.svg": ("🍰", "#ff69b4", "Cake"),
    "pizza.svg": ("🍕", "#ff4500", "Pizza"),
    "donut.svg": ("🍩", "#ba55d3", "Donut"),
    "hotdog.svg": ("🌭", "#cd853f", "Hot Dog"),
    "carrot.svg": ("🥕", "#ff7f50", "Carrot"),
    "broccoli.svg": ("🥦", "#32cd32", "Broccoli"),
    "scissors.svg": ("✂️", "#708090", "Scissors"),
    "biscuit.svg": ("🍪", "#d2691e", "Biscuit Pack"),
    "toothbrush.svg": ("🪥", "#20b2aa", "Toothbrush"),
    "remote.svg": ("📺", "#4682b4", "Remote"),
    "mouse.svg": ("🖱️", "#9370db", "Mouse"),
    "keyboard.svg": ("⌨️", "#2f4f4f", "Keyboard"),
    "laptop.svg": ("💻", "#4169e1", "Laptop"),
    "chips.svg": ("🥔", "#1e90ff", "Chips Packet"),
    "snack.svg": ("🌽", "#ff8c00", "Snack Packet"),
    "chocolate.svg": ("🍫", "#8a2be2", "Chocolate"),
}

for filename, (emoji, color, label) in icons.items():
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <rect width="100" height="100" rx="20" fill="#16213e" stroke="{color}" stroke-width="2"/>
  <text x="50" y="58" font-size="42" text-anchor="middle" dominant-baseline="central">{emoji}</text>
</svg>"""
    (img_dir / filename).write_text(svg_content, encoding="utf-8")

print(f"Generated {len(icons)} SVGs in {img_dir}")
