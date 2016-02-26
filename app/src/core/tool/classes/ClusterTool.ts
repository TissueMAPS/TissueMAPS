class ClusterTool extends ClassificationTool {
    constructor(appInstance: AppInstance) {
        super(
            appInstance,
            'Cluster',
            'Clustering Tool',
            'Cluster objects using the K-means algorithm',
            '/templates/tools/modules/cluster/cluster.html',
            'CLU',
            1025,
            450
          )
    }
}
