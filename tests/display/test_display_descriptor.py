from wof_explorer.display.descriptor import DisplayDescriptor
from wof_explorer.processing.collections import PlaceCollection


def test_descriptor_on_arbitrary_class_returns_generic_display():
    class Dummy:
        display = DisplayDescriptor()

    # Access via class returns None per descriptor contract
    assert Dummy.display is None

    d = Dummy()
    disp = d.display
    assert disp is not None

    # Summary should come from GenericDisplay and include the class name
    summary = disp.summary
    assert isinstance(summary, str)
    assert "Dummy Summary" in summary

    # Descriptor should cache the display object on the instance
    assert d.display is disp


def test_descriptor_maps_placecollection_to_collectiondisplay():
    pc = PlaceCollection(places=[])
    disp = pc.display
    # Should be a specialized display capable of rendering a collection summary
    summary = disp.summary
    assert isinstance(summary, str)
    assert "Collection Summary" in summary
