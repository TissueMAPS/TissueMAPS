angular.module('jtui.module')
.service('moduleService', ['$http', '$q', 'Module', function($http, $q, Module) {

	// Get all available modules
	var modulesDef = $q.defer();
	$http.get('/jtui/get_available_jtmodules').success(function(data) {
        var modulelist = data.jtmodules.modules;
        var registration = data.jtmodules.registration;
        var modules = [];
        for (var i in modulelist) {
        	// Module are only available if they have been registered in the
        	// module_registration.yaml file
        	for (var j in registration) {
	        	if (modulelist[i]['name'] == registration[j]['name']) {
	        		// Make sure that we pass the correct registration info
	        		console.log('module \"' + modulelist[i]['name'] + '\" registered')
		            modules.push(new Module(modulelist[i]['name'],
		                         			modulelist[i]['description'],
		                         			registration[j]['description']));
	        	}
        	}
        }

        modulesDef.resolve(modules);
    });
	this.modules = modulesDef.promise;

    // Get all available pipelines
    var pipelinesDef = $q.defer();
    $http.get('/jtui/get_available_jtpipelines').success(function(data) {
        var pipelines = data.jtpipelines;
        pipelinesDef.resolve(pipelines);
    });
    this.pipelines = pipelinesDef.promise;


    this.getModuleSourceCode = function(moduleName) {

        // TODO: name of the source rather than name of the handle file
        var sourceDef = $q.defer();
        var url = '/jtui/get_module_source_code' +
                  '/' + moduleName;
        $http.get(url).success(function (data) {
            sourceDef.resolve(data)
        });

        return(sourceDef.promise)
    }


}]);
