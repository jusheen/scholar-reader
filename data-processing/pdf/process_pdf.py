import string

import pdf.grobid_client

class PdfStructureParser(object):
    def __init__(self, pdf_hash, structure_map):
        self.pdf_hash = pdf_hash
        self.structure_map = structure_map
        self.pages = structure_map['tokens']['pages']
        self.elements = structure_map['elements']['elementTypes']

    def find_token(self, index):
        for p in self.pages:
            if (index < len(p['tokens'])):
                return p['page'], p['tokens'][index]
            else:
                index -= len(p['tokens'])
        return None


    def get_text(self,spans):
        text = []
        for s in spans:
            direct = s.get('dehyphenizedText')
            if direct:
                text += direct
            else:
                for i in range(s['left'], s['right']):
                    page, token = self.find_token(i)
                    text.append(token['text'])
        return ' '.join(text)

    def union(self, bbox1, bbox2):
        if not bbox1:
            return bbox2
        x1 = min(bbox1[0],bbox2[0])
        y1 = min(bbox1[1],bbox2[1])
        x2 = max(bbox1[0]+bbox1[2], bbox2[0]+bbox2[2])
        y2 = max(bbox1[1]+bbox1[3], bbox2[1]+bbox2[3])
        return [x1, y1, x2-x1, y2-y1]

    def should_combine(self, bbox1, bbox2):
        page1, bb1 = bbox1
        page2, bb2 = bbox2
        return page1 == page2 and (
            abs(bb1[1] - bb2[1]) < 4 # Same y-coordinate
        ) and (
            abs(bb2[0] - bb1[0] - bb1[2]) < 15 # To the right
        )

    def get_bounding_boxes(self, spans):
        bboxes = []
        for s in spans:
            bbox = None
            for i in range(s['left'], s['right']):
                page, token = self.find_token(i)
                page_number = page['pageNumber']
                token_bbox = [token['x'],token['y'],token['width'],token['height']]
                if not bbox:
                    bbox = page_number, token_bbox
                elif self.should_combine(bbox, (page_number, token_bbox)):
                    bbox = bbox[0], self.union(bbox[1], token_bbox)
                else:
                    bboxes.append(bbox)
                    bbox = page_number, token_bbox
            bboxes.append(bbox)
        return bboxes


    def find_cited_paper(self, bib_item_text):
        return 'x'

    def upload(self):
        paper_id = ''
        if not paper_id:
            paper_id = ''

        bib_item_titles = {}
        for ref in self.elements['<bibItem_title>']:
            id = ref['tags'].get('id')
            if id:
                bib_item_titles[id] = self.get_text(ref['spans'])

        for cit in self.elements['<citation_marker>']:
            ref = cit['tags'].get('ref')
            spans = cit['spans']
            if ref:
                bib_item_title = bib_item_titles.get(ref)
                if bib_item_title:
                    cited_paper_id = self.find_cited_paper(self.get_text(spans))
            bbox = self.get_bounding_boxes(spans)
            print('Citation', pdf_hash, bbox, cited_paper_id)

        for sym in self.elements['<symbol>']:
            id = sym['tags'].get('id')
            if id:
                spans = sym['spans']
                bbox = self.get_bounding_boxes(spans)
                print('Symbol', sym, bbox)


if __name__ == '__main__':
    pdf_hash = '3febb2bed8865945e7fddc99efd791887bb7e14f'
    pdf_file='/Users/rodneykinney/data/scholar/grobid/3febb2bed8865945e7fddc99efd791887bb7e14f.pdf'
    s = pdf.grobid_client.get_pdf_structure(pdf_file)
    PdfStructureParser(pdf_hash, s).upload()
