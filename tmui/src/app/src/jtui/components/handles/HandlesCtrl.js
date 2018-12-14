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
angular.module('jtui.handles')
.controller('HandlesCtrl', ['$scope', '$stateParams', 'handlesService', '$timeout', '$uibModal',
            function ($scope, $stateParams, handlesService, $timeout, $uibModal) {

    // Scope inherited from parent (project)
    var currentModuleName = $stateParams.moduleName;

    $scope.getCurrentModuleIndex = function(pipeline) {
        for (i in pipeline) {
            if (pipeline[i].name == currentModuleName) {
                return i;
            }
        }
    }

    $scope.setCurrentModule = function() {
        $scope.index = $scope.getCurrentModuleIndex($scope.project.pipe.description.pipeline);
        $scope.module = $scope.project.handles[$scope.index];
        $scope.source = $scope.project.pipe.description.pipeline[$scope.index].source.substring(
            0, $scope.project.pipe.description.pipeline[$scope.index].source.lastIndexOf('.')
        );
    }

    $scope.setCurrentModule();

    $scope.$watch('project.pipe.description.pipeline', function(pipeline) {
        // The order of modules in the pipeline is tracked for the pipeline
        // description. When this changes, we need to update the order of the
        // corresponding handles as well.
        var moduleNames = pipeline.map(function(m) {
            return m.name;
        })
        $scope.project.handles.sort(function(a, b) {
            if (moduleNames.indexOf(a.name) < moduleNames.indexOf(b.name)) {
                return -1;
            }
            if (moduleNames.indexOf(a.name) > moduleNames.indexOf(b.name)) {
                return 1;
            }
            return 0;
        });
        $scope.setCurrentModule();
    });

    // Get list of upstream output values that are available as input
    // values in the current module
    $scope.getArgList = function(type) {
        var availableArguments = [];
        var pipeline = $scope.project.pipe.description.pipeline;
        var handles = $scope.project.handles;
        var handleNames = handles.map(function(h) {return h.name});
        for (var i in pipeline) {
            var module = pipeline[i];
            // Consider only modules upstream in the pipeline
            if (module.name == $scope.module.name) { break; }
            // Make sure we're dealing with the correct handles object
            var index = handleNames.indexOf(module.name);
            var handle = handles[index];
            for (var j in handle.description.output) {
                var upstreamOutputHandle = handle.description.output[j];
                if ('key' in upstreamOutputHandle) {
                    // Only handles with matching type
                    // TODO: This doesn't take the class hierarchy into account.
                    // For now, we hardcode it for the "Image" and "MaskImage"
                    // classes, but this should be handled more generally.
                    var maskTypes = ['Image', 'MaskImage', 'BinaryImage', 'LabelImage'];
                    var upstreamType = upstreamOutputHandle.type;
                    var isImageType = type == 'Image' && upstreamType.indexOf('Image') !== -1;
                    var isMaskType = type == 'MaskImage' && maskTypes.indexOf(upstreamType) !== -1;
                    var isSameType = type == upstreamOutputHandle.type;
                    if (upstreamOutputHandle.key != null &&
                             (isImageType || isSameType || isMaskType)) {
                        availableArguments.push(
                            handle.description.output[j].key
                        );
                    }
                }
            }
        }
        // Also consider pipeline inputs provided by Jterator
        if (type === 'IntensityImage') {
            var channels = $scope.project.pipe.description.input.channels;
            for (var i in channels) {
                availableArguments.push(channels[i].name);
            }
        }
        if (type === 'SegmentedObjects') {
            var objects = $scope.project.pipe.description.input.objects;
            for (var i in objects) {
                availableArguments.push(objects[i].name);
            }
        }
        return availableArguments;
    }

    $scope.isDuplicate = function(output_arg) {

        var allOutputs = $scope.project.handles.map(function (h) {
            return h.description.output;
        });
        allOutputs = [].concat.apply([], allOutputs);

        var identicalOutputs = _(allOutputs).filter(function (out) {
            if (!_.isNull(out)) {
                return !_.isNull(out.key) && (out.key == output_arg.key);
            }
        });

        // Channels (pipline inputs) have to be considered as well, because
        // they can also be piped.
        var isChannel = $scope.project.pipe.description.input.channels.some(
            function(channel) {
                return channel.name == output_arg.key
            }
        );

        // Objects (pipline inputs) have to be considered as well, because
        // they can also be piped.
        var isObject = $scope.project.pipe.description.input.objects.some(
            function(object) {
                return object.name == output_arg.key
            }
        );

        return identicalOutputs.length > 1 || isChannel || isObject;

    }

    // Determine if input argument is a handle of type `pipe`
    $scope.isPipelineInput = function(input_arg_name) {
        for (var i in $scope.module.description.input) {
            if ($scope.module.description.input[i].name == input_arg_name) {
                if ('key' in $scope.module.description.input[i]){
                    return true;
                } else {
                    return false;
                }
            }
        }
    };

    // Determine if output argument is a handle of type `pipe`
    $scope.isPipelineOutput = function(output_arg_name) {
        for (var i in $scope.module.description.output) {
            if ($scope.module.description.output[i].name == output_arg_name) {
                if ('key' in $scope.module.description.output[i]){
                    return true;
                } else {
                    return false;
                }
            }
        }
    };

    // Determine if input argument has options
    $scope.hasOptions = function(input_arg_name) {
        for (var i in $scope.module.description.input) {
            if ($scope.module.description.input[i].name == input_arg_name) {
                if ('options' in $scope.module.description.input[i]) {
                    return true;
                } else {
                    return false;
                }
            }
        }
    };

    // Determine if input argument is a boolean and if so provide true/false option
    $scope.isBoolean = function(input_arg_name) {
        for (var i in $scope.module.description.input) {
            if ($scope.module.description.input[i].name == input_arg_name) {
                if ($scope.module.description.input[i].type == "Boolean" ||
                        $scope.module.description.input[i].type == "Plot") {
                    return true;
                } else {
                    false;
                }
            }
        }
    };
    $scope.boolOptions = [true, false]

    $scope.getHelpForModule = function(moduleName) {
        // console.log('get help for module \"' + moduleName + '\"')

        // Use the name of the executable file
        var ixPipe = $scope.project.pipe.description.pipeline.map(function(e) { 
                return e.name;
            }).indexOf(moduleName);
        var moduleFilename = $scope.project.pipe.description.pipeline[ixPipe].module;
        moduleName = moduleFilename.split(/([^\/\.]+)\.\w+$/)[1];

        var modalInst = $uibModal.open({
            templateUrl: 'components/handles/modals/handlesHelp.html',
            resolve: {
                help: ['handlesService', function(handlesService){
                            return handlesService.getHelp(moduleName).then(function(helpFile) {
                                // console.log(helpFile)
                                return helpFile;
                            });
                }]
            },
            controller: 'HandlesHelpCtrl'
        });

        modalInst.result.then(function() {});

    };


    $scope.convert2yaml = function(inarg, $index) {
        // console.log('input value:', typeof inarg.value)
        var newinarg = jsyaml.load(inarg.value);
        // console.log('converted value: '. newinarg)
        $scope.module.description.input[$index].value = newinarg;
        // console.log('input value:', typeof newinarg)
    };


}]);

