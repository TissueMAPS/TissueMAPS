// Copyright 2016, 2018 University of Zurich
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
angular.module('jtui.module')
.service('moduleService', ['$http', '$q', 'Module', function($http, $q, Module) {

    // Get all available modules
    var modulesDef = $q.defer();
    $http.get('/jtui/available_modules').success(function(data) {
        var modulelist = data.jtmodules.modules;
        var registration = data.jtmodules.registration;
        var modules = [];
        for (var i in modulelist) {
            for (var j in registration) {
                if (modulelist[i]['name'] == registration[j]['name']) {
                    // Make sure that we pass the correct registration info
                    // console.log('module \"' + modulelist[i]['name'] + '\" registered')
                    modules.push(new Module(modulelist[i]['name'],
                                             modulelist[i]['description'],
                                             registration[j]['description']));
                }
            }
        }

        modulesDef.resolve(modules);
    });
    this.modules = modulesDef.promise;

    this.getModuleSourceCode = function(moduleName) {
        var sourceDef = $q.defer();
        var url = '/jtui/module_source_code?module_name=' + moduleName;
        $http.get(url).success(function (data) {
            sourceDef.resolve(data)
        });

        return(sourceDef.promise)
    }


}]);
