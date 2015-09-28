interface Serialized<T> {

}

interface Serializable<T> {
    serialize(): ng.IPromise<Serialized<T>>;
}
