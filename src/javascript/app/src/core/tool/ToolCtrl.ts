/**
 * The base class for all tool controllers (i.e. angular controllers that are
 * created for the respective tool window).
 * The actual sendRequest method that will send its payload to the right server
 * route will be dynamically monkeypatched onto the controller object by the
 * tmToolWindow directive.
 * This method can't be marked abstract due to the way objects of this class
 * are created. 
 */
class ToolCtrl {
    sendRequest(payload: any): ng.IPromise<any> {
        return <ng.IPromise<any>>{};
    }
}

