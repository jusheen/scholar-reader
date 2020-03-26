import string

import pdf.grobid_client
from common.models import BoundingBox as BoundingBoxModel
from common.models import (Citation, CitationPaper, Entity, EntityBoundingBox,
                           Paper, Summary, output_database)
from entities.citations.commands.upload_citations import CitationData


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

    def union(self, bbox1: BoundingBoxModel, bbox2: BoundingBoxModel):
        if not bbox1:
            return bbox2
        x1 = min(bbox1.left,bbox2.left)
        y1 = min(bbox1.top,bbox2.top)
        x2 = max(bbox1.left+bbox1.width, bbox2.left+bbox2.width)
        y2 = max(bbox1.top+bbox1.height, bbox2.top+bbox2.height)
        return BoundingBoxModel(page = bbox1.page,
                                left = x1, top = y1, width = x2-x1, height=y2-y1)

    def should_combine(self, bbox1: BoundingBoxModel, bbox2: BoundingBoxModel):
        return bbox1.page == bbox2.page and (
            abs(bbox1.top - bbox2.top) < 4 # Same y-coordinate
        ) and (
            abs(bbox2.left - bbox1.left - bbox1.width) < 15 # To the right
        )

    def get_bounding_boxes(self, spans):
        bboxes = []
        for s in spans:
            bbox = None
            for i in range(s['left'], s['right']):
                page, token = self.find_token(i)
                page_number = page['pageNumber']
                token_bbox = BoundingBoxModel(
                    page = page_number,
                    left = token['x'],
                    top = token['y'],
                    width = token['width'],
                    height=token['height']
                )
                if not bbox:
                    bbox = token_bbox
                elif self.should_combine(bbox, token_bbox):
                    bbox = self.union(bbox, token_bbox)
                else:
                    bboxes.append(bbox)
                    bbox = token_bbox
            bboxes.append(bbox)
        return bboxes


    def find_cited_paper(self, bib_item_text):
        return 'x'

    def get_symbols(self):
        for sym in self.elements['<symbol>']:
            id = sym['tags'].get('id')
            if id:
                spans = sym['spans']
                bbox = self.get_bounding_boxes(spans)
                print('Symbol', sym, bbox)

    def get_citations(self) -> CitationData:
        locations = {}
        s2_ids_of_citations = {}
        s2_ids = {}
        return CitationData(
            arxiv_id = None,
            s2_id = pdf_hash,
            citation_locations=locations,
            key_s2_ids=s2_ids_of_citations,
            s2_data = s2_ids
        )


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

        self.get_symbols()


if __name__ == '__main__':
    pdf_hash = '3febb2bed8865945e7fddc99efd791887bb7e14f'
    pdf_file='/Users/rodneykinney/data/scholar/grobid/3febb2bed8865945e7fddc99efd791887bb7e14f.pdf'
    s = pdf.grobid_client.get_pdf_structure(pdf_file)
    PdfStructureParser(pdf_hash, s).upload()
