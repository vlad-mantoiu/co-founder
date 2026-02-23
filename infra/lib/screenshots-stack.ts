import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import { Construct } from 'constructs';

export class ScreenshotsStack extends cdk.Stack {
  public readonly screenshotsBucket: s3.Bucket;
  public readonly screenshotsDistributionDomain: string;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 1. Private S3 bucket — no public access, OAC handles reads
    // S3_MANAGED encryption (not KMS) — avoids OAC KMS complexity per MarketingStack precedent
    this.screenshotsBucket = new s3.Bucket(this, 'ScreenshotsBucket', {
      bucketName: 'cofounder-screenshots',
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN,        // Production bucket — never auto-delete
      encryption: s3.BucketEncryption.S3_MANAGED,     // SSE-S3, not KMS
      versioned: false,                                // No versioning needed for screenshots
    });

    // 2. OAC origin — L2 construct auto-creates OAC + scoped bucket policy
    const s3Origin = origins.S3BucketOrigin.withOriginAccessControl(this.screenshotsBucket);

    // 3. Cache policy — 1-year immutable (PNG files addressed by build ID, never mutated)
    // brotli disabled: PNG is already compressed binary — brotli wastes CPU with no benefit
    const cachePolicy = new cloudfront.CachePolicy(this, 'ScreenshotsCachePolicy', {
      cachePolicyName: 'Screenshots-Immutable-1yr',
      defaultTtl: cdk.Duration.days(365),
      minTtl: cdk.Duration.days(365),
      maxTtl: cdk.Duration.days(365),
      enableAcceptEncodingGzip: true,
      enableAcceptEncodingBrotli: false,
      queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
      cookieBehavior: cloudfront.CacheCookieBehavior.none(),
    });

    // 4. Response headers policy — enforce immutable cache-control at CDN edge
    // override: true ensures this header overrides any S3 origin cache headers
    const responseHeadersPolicy = new cloudfront.ResponseHeadersPolicy(
      this,
      'ScreenshotsResponseHeadersPolicy',
      {
        responseHeadersPolicyName: 'Screenshots-ImmutableCache',
        comment: 'Enforce immutable cache-control for build screenshots',
        customHeadersBehavior: {
          customHeaders: [
            {
              header: 'cache-control',
              value: 'max-age=31536000, immutable',
              override: true,
            },
          ],
        },
      }
    );

    // 5. CloudFront Distribution
    // No custom domain — default CloudFront domain (dXXXX.cloudfront.net)
    // No Route53 alias needed; backend writes the CF domain to the DB at build time
    const distribution = new cloudfront.Distribution(this, 'ScreenshotsDistribution', {
      defaultBehavior: {
        origin: s3Origin,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy,
        responseHeadersPolicy,
        compress: false,                                       // PNG already compressed
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
      },
      priceClass: cloudfront.PriceClass.PRICE_CLASS_200,
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
    });

    // Expose CF domain for ComputeStack to inject as env var
    this.screenshotsDistributionDomain = distribution.distributionDomainName;

    // 6. CfnOutputs — for operational reference and CI/CD tooling
    new cdk.CfnOutput(this, 'ScreenshotsBucketName', {
      value: this.screenshotsBucket.bucketName,
      description: 'S3 bucket name for build screenshots',
      exportName: 'CoFounderScreenshotsBucketName',
    });

    new cdk.CfnOutput(this, 'ScreenshotsDistributionDomain', {
      value: this.screenshotsDistributionDomain,
      description: 'CloudFront distribution domain for serving build screenshots',
      exportName: 'CoFounderScreenshotsDistributionDomain',
    });
  }
}
