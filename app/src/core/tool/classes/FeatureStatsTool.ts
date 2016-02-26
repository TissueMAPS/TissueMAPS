class FeatureStatsTool extends Tool {
    constructor(appInstance: AppInstance) {
        super(
            appInstance,
            'FeatureStats',
            'Feature Statistics',
            'Compute some basic statistics',
            '/templates/tools/modules/featurestats/feature-stats.html',
            '<i class=\"fa fa-bar-chart\"></i>',
            850,
            600
          )
    }

    handleResult(res: ToolResult) {
        console.log(res);
    }
}
