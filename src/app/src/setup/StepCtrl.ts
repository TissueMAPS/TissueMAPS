interface UIScrollingAdapter {
     // - a boolean value indicating whether there are any pending load requests.
    isLoading?: boolean;
    // - a reference to the item currently in the topmost visible position.
    topVisible?: boolean;
    // - a reference to the DOM element currently in the topmost visible position.
    topVisibleElement?: any;
    // - a reference to the scope created for the item currently in the topmost visible position.
    topVisibleScope?: any;
    // - setting disabled to true disables scroller's scroll/resize events handlers. This can be useful if you have multiple scrollers within the same scrollViewport and you want to prevent some of them from responding to the events.
    disabled?: boolean;

    isBOF?: () => boolean;
    isEOF?: () => boolean;
    reload?: () => void;
}


class StepCtrl {

    currentStageIndex: number;
    currentStepIndex: number;
    uiScrollingAdapter: UIScrollingAdapter = {};

    static $inject = ['workflow', 'workflowService', '$state', '$scope', '$rootScope', '$uibModal', 'experiment', '$http'];

    constructor(public workflow: Workflow,
                private _workflowService,
                private _$state,
                private _$scope,
                private _$rootScope,
                private _$uibModal,
                private _experiment,
                private _$http) {
        this.workflow = this._workflowService.workflow;
        var stageName = this._$state.params.stageName;
        var stepName = this._$state.params.stepName;
        this._$rootScope.$on('resubmission', () => {
            console.log('reload scrolling adapter for step: ', stepName)
            this.uiScrollingAdapter.reload();
        })
        this.workflow.stages.map((stage, stageIndex) => {
            if (stage.name == stageName) {
                this.currentStageIndex = stageIndex;
                stage.steps.forEach((step, stepIndex) => {
                    if (step.name == stepName) {
                        this.currentStepIndex = stepIndex;
                    }
                });
            }
        });
    }

    hasExtraArgs() {
        var stageIdx = this.currentStageIndex;
        var stepIdx = this.currentStepIndex;
        if (this.workflow.stages[stageIdx].steps[stepIdx] == undefined) {
            return false;
        } else if (this.workflow.stages[stageIdx].steps[stepIdx].extra_args) {
            return true;
        } else {
            return false;
        }
    }

    jobsDataSource = {
        get: (index, count, success) => {
            console.log(index);
            var experimentId = this._experiment.id;
            var stepName = this._$state.params.stepName;
            var url = '/api/experiments/' + experimentId + '/workflow/status/jobs' +
                      '?index=' + index + '&step_name=' + stepName + '&batch_size=' + count;
            this._$http.get(url).then((resp) => {
                var jobs = resp.data.data;
                console.log(jobs)
                success(jobs);
            });
        }
    };

}

angular.module('tmaps.ui').controller('StepCtrl', StepCtrl);
