import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as targets from 'aws-cdk-lib/aws-route53-targets';
import { Construct } from 'constructs';
import * as path from 'path';

export class MarketingStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 1. Import hosted zone (already cached in cdk.context.json as Z100112320CO99MQG9VJS)
    const hostedZone = route53.HostedZone.fromLookup(this, 'HostedZone', {
      domainName: 'getinsourced.ai',
    });

    // 2. ACM Certificate (apex + www SAN, DNS validation)
    // Must be in us-east-1 for CloudFront — satisfied since all stacks are us-east-1
    const certificate = new acm.Certificate(this, 'Certificate', {
      domainName: 'getinsourced.ai',
      subjectAlternativeNames: ['www.getinsourced.ai'],
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });

    // 3. Private S3 bucket — no public access, no website hosting (OAC uses REST API endpoint)
    const bucket = new s3.Bucket(this, 'MarketingBucket', {
      bucketName: 'getinsourced-marketing',
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,           // Production bucket — never auto-delete
      encryption: s3.BucketEncryption.S3_MANAGED,        // SSE-S3 (not KMS — avoids OAC KMS complexity)
      versioned: false,                                   // Hash-busting handles asset versioning
    });

    // 4. CloudFront Function for www redirect + clean URL rewriting
    const cfFunction = new cloudfront.Function(this, 'UrlFunction', {
      functionName: 'marketing-url-handler',
      code: cloudfront.FunctionCode.fromFile({
        filePath: path.join(__dirname, '../functions/url-handler.js'),
      }),
      runtime: cloudfront.FunctionRuntime.JS_2_0,
    });

    // 5. Cache policies
    // HTML pages: short TTL (5 min) — invalidated on every deploy
    const htmlCachePolicy = new cloudfront.CachePolicy(this, 'HtmlCachePolicy', {
      cachePolicyName: 'Marketing-Html-5min',
      defaultTtl: cdk.Duration.minutes(5),
      minTtl: cdk.Duration.seconds(0),
      maxTtl: cdk.Duration.minutes(5),
      enableAcceptEncodingGzip: true,
      enableAcceptEncodingBrotli: true,
      queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
      cookieBehavior: cloudfront.CacheCookieBehavior.none(),
    });

    // Hashed static assets: 1-year TTL — content-hash filenames make this safe
    const assetCachePolicy = new cloudfront.CachePolicy(this, 'AssetCachePolicy', {
      cachePolicyName: 'Marketing-Assets-1yr',
      defaultTtl: cdk.Duration.days(365),
      minTtl: cdk.Duration.days(365),
      maxTtl: cdk.Duration.days(365),
      enableAcceptEncodingGzip: true,
      enableAcceptEncodingBrotli: true,
      queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
      cookieBehavior: cloudfront.CacheCookieBehavior.none(),
    });

    // 6. OAC origin — L2 construct auto-creates OAC + auto-adds scoped bucket policy
    const s3Origin = origins.S3BucketOrigin.withOriginAccessControl(bucket);

    // 6b. Custom response headers policy — replaces managed SECURITY_HEADERS preset
    // Managed preset (67f7725c) has no CSP and no Permissions-Policy; source-controlling is required
    const marketingResponseHeadersPolicy = new cloudfront.ResponseHeadersPolicy(
      this,
      'MarketingResponseHeadersPolicy',
      {
        responseHeadersPolicyName: 'Marketing-SecurityHeaders',
        comment: 'Custom security headers for getinsourced.ai - v0.4',
        securityHeadersBehavior: {
          contentSecurityPolicy: {
            override: true,
            contentSecurityPolicy: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",  // Next.js static export: self.__next_f.push() inline scripts
              "style-src 'self' 'unsafe-inline'",   // Framer Motion: sets opacity/transform via inline style=
              "font-src 'self'",                    // Geist/Space Grotesk self-hosted via next/font
              "img-src 'self' data:",               // data: for any future base64 images
              "connect-src 'self' https://formsubmit.co",
              "media-src 'none'",
              "object-src 'none'",
              "child-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'self'",             // 'self' not 'none': allows Google Rich Results Test preview iframe
              "upgrade-insecure-requests",
            ].join('; '),
          },
          contentTypeOptions: { override: true },
          frameOptions: {
            frameOption: cloudfront.HeadersFrameOption.SAMEORIGIN,
            override: true,
          },
          referrerPolicy: {
            referrerPolicy: cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
            override: true,
          },
          strictTransportSecurity: {
            accessControlMaxAge: cdk.Duration.seconds(63072000), // 2 years (up from 1 year in managed preset)
            includeSubdomains: true,                             // all getinsourced.ai subdomains are HTTPS-only
            preload: false,                                      // do not commit to preload list — near-permanent
            override: true,
          },
          xssProtection: {
            protection: true,
            modeBlock: true,
            override: true,
          },
        },
        // Permissions-Policy must use customHeadersBehavior — not a native securityHeadersBehavior field
        customHeadersBehavior: {
          customHeaders: [
            {
              header: 'Permissions-Policy',
              value: [
                'camera=()',
                'microphone=()',
                'geolocation=()',
                'payment=()',
                'usb=()',
                'magnetometer=()',
                'accelerometer=()',
                'gyroscope=()',
                'display-capture=()',
                'interest-cohort=()',
              ].join(', '),
              override: true,
            },
          ],
        },
      }
    );

    // 7. CloudFront Distribution
    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      defaultBehavior: {
        origin: s3Origin,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: htmlCachePolicy,
        compress: true,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        functionAssociations: [{
          function: cfFunction,
          eventType: cloudfront.FunctionEventType.VIEWER_REQUEST,
        }],
        responseHeadersPolicy: marketingResponseHeadersPolicy,
      },
      additionalBehaviors: {
        '_next/static/*': {
          origin: s3Origin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: assetCachePolicy,
          compress: true,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        },
        'images/*': {
          origin: s3Origin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: assetCachePolicy,  // reuse existing 365-day TTL policy
          compress: true,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        },
      },
      domainNames: ['getinsourced.ai', 'www.getinsourced.ai'],
      certificate,
      defaultRootObject: 'index.html',
      priceClass: cloudfront.PriceClass.PRICE_CLASS_200,
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      errorResponses: [
        // S3 returns 403 for missing keys with OAC (hides 404 to prevent bucket enumeration)
        { httpStatus: 403, responsePagePath: '/404.html', responseHttpStatus: 404, ttl: cdk.Duration.minutes(5) },
        { httpStatus: 404, responsePagePath: '/404.html', responseHttpStatus: 404, ttl: cdk.Duration.minutes(5) },
        // 5xx errors: keep original status, short TTL to avoid caching transient errors
        { httpStatus: 500, responsePagePath: '/404.html', responseHttpStatus: 500, ttl: cdk.Duration.seconds(5) },
        { httpStatus: 502, responsePagePath: '/404.html', responseHttpStatus: 502, ttl: cdk.Duration.seconds(5) },
        { httpStatus: 503, responsePagePath: '/404.html', responseHttpStatus: 503, ttl: cdk.Duration.seconds(5) },
        { httpStatus: 504, responsePagePath: '/404.html', responseHttpStatus: 504, ttl: cdk.Duration.seconds(5) },
      ],
    });

    // 8. Route53 alias records — A (IPv4) + AAAA (IPv6) for both apex and www
    // The CloudFront Function handles the www -> apex 301 redirect
    for (const [recordId, recordName] of [['Apex', 'getinsourced.ai'], ['Www', 'www.getinsourced.ai']] as const) {
      new route53.ARecord(this, `${recordId}ARecord`, {
        zone: hostedZone,
        recordName,
        target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(distribution)),
      });
      new route53.AaaaRecord(this, `${recordId}AaaaRecord`, {
        zone: hostedZone,
        recordName,
        target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(distribution)),
      });
    }

    // 9. CfnOutputs for Phase 21 (Marketing CI/CD — invalidation + deploy automation)
    new cdk.CfnOutput(this, 'DistributionId', {
      value: distribution.distributionId,
      description: 'CloudFront Distribution ID for cache invalidation',
      exportName: 'CoFounderMarketingDistributionId',
    });
    new cdk.CfnOutput(this, 'DistributionDomain', {
      value: distribution.distributionDomainName,
      description: 'CloudFront Distribution domain name',
      exportName: 'CoFounderMarketingDistributionDomain',
    });
    new cdk.CfnOutput(this, 'BucketName', {
      value: bucket.bucketName,
      description: 'S3 bucket name for marketing site content',
      exportName: 'CoFounderMarketingBucketName',
    });
  }
}
