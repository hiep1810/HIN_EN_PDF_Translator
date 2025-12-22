try:
    from surya.layout import LayoutPredictor
    print("Found LayoutPredictor")
except ImportError:
    print("No LayoutPredictor found in surya.layout")
    import surya.layout
    print(dir(surya.layout))
