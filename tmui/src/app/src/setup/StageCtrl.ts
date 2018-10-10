// Copyright (C) 2016-2018 University of Zurich.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
class StageCtrl {

    currentStageIndex: number
    currentStepIndex: number;

    static $inject = ['workflow', 'workflowService', '$state', '$scope'];

    constructor(public workflow: Workflow,
                private _workflowService,
                private _$state,
                private _$scope) {
        // console.log(this.workflow)
        this.workflow = this._workflowService.workflow;
        var stageName = this._$state.params.stageName;
        var stepName = this._$state.params.stepName;
        this.workflow.stages.map((stage, stageIndex) => {
            if (stage.name == stageName) {
                this.currentStageIndex = stageIndex;
            }
        })
        var stageIdx = this.currentStageIndex;
        if (this.workflow.stages[stageIdx] == undefined) {
            // TODO: different plates instead of steps?
            this._$state.go('plate', {
                stageName: this.workflow.stages[stageIdx].name
            });
        } else {
            this.workflow.stages[stageIdx].steps.map((step, stepIndex) => {
                if (step.name == stepName) {
                    this.currentStepIndex = stepIndex;
                }
            });
            var stepIdx = this.currentStepIndex;
            if (this.workflow.stages[stageIdx].steps[stepIdx] != undefined) {
                var selectedStep = this.workflow.stages[stageIdx].steps[stepIdx];
            } else {
                var selectedStep = this.workflow.stages[stageIdx].steps[0];
            }
            this.goToStep(selectedStep)
        }
    }

    isInStep(step: WorkflowStep) {
        var idx = this.currentStepIndex;
        return this.workflow.stages[this.currentStageIndex].steps[idx].name === step.name;
    }

    goToStep(step: WorkflowStep) {
        var idx = this.currentStageIndex;
        this.currentStepIndex = this.workflow.stages[idx].steps.indexOf(step);
        // console.log('go to step: ', step)
        this._$state.go('setup.step', {
            stepName: step.name
        });
    }

}

angular.module('tmaps.ui').controller('StageCtrl', StageCtrl);

angular.module('tmaps.ui').directive('tmArgumentInput', function() {
    return {
        restrict: 'E',
        scope: {
            arg: '='
        },
        controller: ['$scope', function($scope) {
            var widgetType;
            var argumentType = $scope.arg.type;
            var hasChoices = $scope.arg.choices !== null;

            if (hasChoices) {
                if ($scope.arg.choices.indexOf(true) > -1 ) {
                    widgetType = 'checkbox';
                } else {
                    widgetType = 'dropdown';
                }
            } else {
                widgetType = 'textInput';
            }

            if ($scope.arg.value == null) {
                $scope.arg.value = $scope.arg.default;
            }
            $scope.arg.required = $scope.arg.required || $scope.arg.default !== null;
            $scope.widgetType = widgetType;

            $scope.shouldAlert = function() {
                return $scope.arg.required &&
                       ($scope.arg.value === undefined ||
                        $scope.arg.value === '' ||
                        $scope.arg.value === null);
            };
        }],
        templateUrl: '/src/setup/tm-argument-input.html'
    };
})
