angular.module('jtui.handles')
.service('handlesService', ['$http', '$q', function($http, $q) {

	function getHelp(moduleName) {
		var helpDef = $q.defer();
		$http.get('/jtui/help/' + moduleName).success(function(data) {
	        helpDef.resolve(data);
	    });

		return(helpDef.promise);
	}

	return({
		getHelp: getHelp
	});

}]);
