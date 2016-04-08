from tmaps.tool.result import LabelResult


class ClassifierResult(LabelResult):
    def __init__(self, *args, **kwargs):
        super(ClassifierResult, self).__init__(
            *args, result_type='ClassifierResult', **kwargs
        )
