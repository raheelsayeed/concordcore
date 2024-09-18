from functools import cached_property
import os, logging, jinja2
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol
from variables.record import Record

from core.assessment import EvaluatedAssessmentRecord
from core.recommendation import EvaluatedRecommendation
from core.evaluation import EvaluatedRecord
from core.concord import Concord
from outomes.outcome import Advisory

log = logging.getLogger(__name__)

# IN:
# Persona: for people or providers or ?
# concord: parsed guidance
# base_template: any base tempalte this should be applied to -- must be jinja2

class RenderingModal(Enum):
    PHONE       = auto()
    EHR         = auto()
    VOICE       = auto()


@dataclass
class RenderingProtocol(Protocol):

    id: str
    concord: Concord
    base_template = None
    modal: RenderingModal = RenderingModal.EHR

    def render_record(self, records: Record):
        ... 

    def render_assessment(self, evaluated_record: EvaluatedRecord):
        pass 

    def render_recommendation(self, evaluated_recommendation: EvaluatedRecommendation):
        pass




@dataclass
class BaseRenderer(RenderingProtocol):

    concord: Concord
    """Instance of Concord"""

    base_template = None
    """Base template"""

    modal: RenderingModal = RenderingModal.EHR
    """Modal (EHR, Phone, Voice)"""

    cpg_folder = 'cpgs'
    """CPG folder"""

    template_env = None 
    """Template Environment folder"""




    def rendering_folder_path(self):
        if self.concord.cpg.rendering_template_path:
            return self.cpg_folder + '/' + self.concord.cpg.rendering_template_path
        return None

    def __post_init__(self):
        if not self.rendering_folder_path():
            return
        log.info(f'folderpath={self.rendering_folder_path()}')
        template_loader = jinja2.FileSystemLoader(searchpath=self.rendering_folder_path())
        self.template_env = jinja2.Environment(loader=template_loader, extensions=['jinja_markdown.MarkdownExtension'])


    # Record -------------------------------------------------------------
    @cached_property
    def default_record_template(self):
        """Default template for rendering user `Record`"""
        try: 
            filename = "record_template.html"
            template = self.template_env.get_template(filename)
            return template
        except Exception as e:
            log.warning(f'Default `record_template` not found for `Record` at path={self.rendering_folder_path()}')
            return None

    def template_for_record(self, record: Record = None):
        try:
            template = self.template_env.get_template(record.id+'.html')
            return template
        except jinja2.exceptions.TemplateNotFound as e:
            template = self.default_record_template
            return template
        except Exception as e:
            log.warning(f'Record_template not found for Record={record.id} at path={self.rendering_folder_path()}')
            return None
    
    def render(self, record=Record):
        try: 
            template = self.template_for_record(record=record)
            return template.render(record=record)
        except Exception as e:
            log.warning(f'{e}')
            return None

    # Record -------------------------------------------------------------


        



    def render_evaluated_record(self, evaluated_record: EvaluatedRecord):
        try:
            template = self.template_env.get_template(evaluated_record.record.id+'.html')
            return template.render(record=evaluated_record)
        except jinja2.exceptions.TemplateNotFound as e:
            template = self.template_env.get_template('base_variable_template.html')
            return template.render(record=evaluated_record)
        except Exception as e:
            log.warning(f'Rendering_template not found for Assessment={evaluated_record.record.id} at path={self.rendering_folder_path()}')
            return None

    def render_assessment(self, evaluated_assessment: EvaluatedAssessmentRecord):
        try:
            template = self.template_env.get_template(evaluated_assessment.record.id+'.html')
            return template.render(assessment=evaluated_assessment)
        except jinja2.exceptions.TemplateNotFound as e:
            template = self.template_env.get_template('assessment_template.html')
            return template.render(assessment=evaluated_assessment)
        except Exception as e:
            log.warning(f'Rendering_template not found for Assessment={evaluated_assessment.record.id} at path={self.rendering_folder_path()}')
            return None
    def render_variable_record(self, record: EvaluatedRecord):
        pass


    def render_recommendation(self, evaluated_recommendation: EvaluatedRecommendation):
        # as_dict = evaluated_recommendation.as_dict()
        # con.print('recommendation_dict=', as_dict)
        try:
            template = self.template_env.get_template(evaluated_recommendation.recommendation.id+'.html')
            return template.render(recommendation=evaluated_recommendation)
        except jinja2.exceptions.TemplateNotFound as e:
            template = self.template_env.get_template('recommendation_template.html')
            return template.render(recommendation=evaluated_recommendation)
        except Exception as e:
            log.warning(f' Rendering_template not found for Recommendation={evaluated_recommendation.recommendation.id}')
            return None

    def render_assessments(self):
        try:
            evaluated_assessments = self.concord.assessment_result.context.evaluation_list        
            rendered_html = [self.render_assessment(ea) for ea in evaluated_assessments]
            return rendered_html
        except Exception as e:
            log.error(e)
            return None
                
    def render_recommendations(self):
        try:
            rendered_html = [self.render_recommendation(ea) for ea in self.concord.recommendation_result.recommendations]
            return rendered_html
        except Exception as e:
            log.error(e)
            return None
    
    def render_evaluated_records(self):
        try: 
            rendered_html = [self.render_evaluated_record(er) for er in self.concord.sufficiency_evaluated_records]
            return rendered_html
        except Exception as e:
            log.error(e)
            return None

    def render(self):
        PAGE_TEMPLATE_FILENAME = 'page_template.html'

        d = { }
        d['template_id'] = self.id
        d['assessments'] = self.render_assessments() or self.concord.assessment_result.context.evaluation_list
        d['recommendations'] = self.render_recommendations() or self.concord.recommendation_result.recommendations
        d['records'] = self.render_evaluated_records() or self.concord.sufficiency_evaluated_records
        d.update(self.concord.cpg.as_dict())
        import datetime 
        d['dated'] = datetime.datetime.now()

        # from ..outomes import Advisory
        # d['advisories'] = Advisory.All()

        base_template = self.template_env.get_template('page_template.html')
        html = base_template.render(**d)

        return html


    def render_page(self):

        html = self.render()
        
        with open('output/output.html','w',encoding = 'utf-8') as f:
            f.write(html)
            f.close()
            # os.system('cp renderer/cards_tempalates/style.css output/style.css')
            os.system('open output/output.html')
        return html
        
