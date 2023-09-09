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
            order_length, order_fabric, order_uv = self.get_xml_values(root)
        else:
            order_length = "?"
            order_fabric = "?"
            order_uv = ""

        return order_length, order_fabric, order_uv

    def get_xml_values(self, root):
        order_length = "?"
        order_fabric = "?"
        order_uv = ""

        for elem in root.iter():
            if "lineType" in elem.attrib and elem.attrib["lineType"] == "PlotLine":
                order_uv = "UV"
                break

        for elem in root.iter():
            if "achievedLength" in elem.attrib:
                order_length = "{:.2f}".format(float(elem.attrib["achievedLength"]) / 100)
                order_length += "m"
            if "description" in elem.attrib:
                order_fabric = elem.attrib["description"]

        return order_length, order_fabric, order_uv
