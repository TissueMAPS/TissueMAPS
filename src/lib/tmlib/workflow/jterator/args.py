from tmlib.workflow.args import Argument
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.args import ExtraArguments
from tmlib.workflow import register_batch_args
from tmlib.workflow import register_submission_args
from tmlib.workflow import register_extra_args


@register_batch_args('jterator')
class JteratorBatchArguments(BatchArguments):

    plot = Argument(
        type=bool, default=False, flag='p', disabled=True,
        help='whether plotting should be activated'
    )

    batch_size = Argument(
        type=int, help='number of sites that should be processed per job',
        default=1, flag='b'
    )


@register_submission_args('jterator')
class JteratorSubmissionArguments(SubmissionArguments):

    pass


def get_names_of_existing_pipelines(experiment):
    '''Gets names of all existing jterator pipelines for a given experiment.

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment

    Returns
    -------
    List[str]
        names of jterator pipelines
    '''
    import os
    from tmlib.workflow.jterator.project import list_projects
    directory = os.path.join(experiment.workflow_location, 'jterator')
    if not os.path.exists(directory):
        return []
    else:
        return [
            os.path.basename(project)
            for project in list_projects(directory)
        ]


@register_extra_args('jterator')
class JteratorExtraArguments(ExtraArguments):

    pipeline = Argument(
        type=str, help='name of the pipeline that should be processed',
        required=True, flag='p', get_choices=get_names_of_existing_pipelines
    )
