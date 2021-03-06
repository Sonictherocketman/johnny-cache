# Johnny Cache

> This Software is in Beta

*A simple forward caching proxy. Useful for reducing the bandwidth of polling or crawling public sites.*

I built this because a feed reader I run, called [Pine.blog](https://pine.blog), constantly needs to crawl sites and poll feeds, and doing all of that for thousands of sites can eat up bandwidth, and really overload some sites (especially those on shared hosting).

This caching proxy is meant to be a forward proxy between your servers and the public internet. Responses from any requests are heavily cached using a variety of methods.

Johnny Cache also supports persisting the request cache across restarts with no additional configuration. Persisted caches are backed by either Redis (for shared caches) or a local file cache (default).


## Supported Caching Methods

Johnny will aggressively cache responses to ensure that your requests only reach the site in question when it absolutely has to, and you can configure this behavior to fit your needs.

Johnny checks for cached requests using:
- Proxy Cache `Expires` Headers
- HTTP `Last-Modified` Headers
- HTTP `ETag` Headers

When a request misses the cache due to an expired cache entry, an `If-Modified-Since` or `If-None-Match` header (depending on which is available) is added to your request giving the destination server one last chance to leverage the cache.


## Usage

Johnny is Docker-ready. If you have Docker-Compose installed, then simply run the following:

```
$ docker-compose up -d
```

### Adding to Docker-Compose

If you already have a Docker-Compose based application, then you can add Johnny to your stack by adding the following to your `docker-compose.yml`.

```
  cache_proxy:
    build:
      # Change the tag to whichever version you'd prefer.
      context: https://github.com/Sonictherocketman/johnny-cache#master
      dockerfile: Dockerfile
```


## Options

For a list of all the supported options, please refer to `docker-compose.yml`.

- `MAX_CACHE_SECONDS`: The maximum number of seconds to keep a response in the cache (default 0 - forever). A negative value will cause caching to be disabled.
- `LOG_LEVEL`: The level that the proxy will log.
- `LOG_LOCATION`: Where to store the logs. The defaulr value of '-' will log to stdout.

### Local Cache Settings

- `CACHE_LOCATION`: The location to store/load the proxy cache.
- `CACHE_NAME`: The name of the cache file.

### Redis Cache Settings

- `REDIS_URL`: The URL of the redis instance you'd like to use as a cache store.

## Supported Cache Operations

Johnny supports the following `Cache-Control` directives:

- `no-store`: Johnny will simply forward your request with no additional information attached. This entirely bypasses the cache.


## Contributing

Pull Requests are welcome. I may not be the best at responding to feedback, but I'll do my best. Features that go out of scope will be rejected.

Please ensure all linting and testing passes before making your PR (use `./preflight` to be sure).

