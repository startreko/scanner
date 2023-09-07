import os
import xml.etree.ElementTree as ET

class XMLScanner:
    def __init__(self, xml_directory):
        self.xml_directory = xml_directory

    def scan_xml(self, code):
        filename = os.path.join(self.xml_directory, f"{code}.xml")
        if os.path.isfile(filename):
            tree = ET.parse(filename)
            root = tree.getroot()
            order_length, order_fabric, order_property = self.get_xml_values(root)
        else:
            order_length = "?"
            order_fabric = "?"
            order_property = ""

        return order_length, order_fabric, order_property

    def get_xml_values(self, root):
        order_length = "?"
        order_fabric = "?"
        order_property = ""

        for elem in root.iter():
            if "lineType" in elem.attrib and elem.attrib["lineType"] == "SpecialLine":
                order_property = "SpecialProperty"
                break

        for elem in root.iter():
            if "achievedValue" in elem.attrib:
                order_length = "{:.2f}".format(float(elem.attrib["achievedValue"]) / 100)
                order_length += "m"
            if "description" in elem.attrib:
                order_fabric = elem.attrib["description"]

        return order_length, order_fabric, order_property
